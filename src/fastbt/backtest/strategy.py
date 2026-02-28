"""
fastbt.backtest.strategy
========================
Abstract Strategy base class with:
- State machine : IDLE → ACTIVE → DONE  (managed by engine via run_one_cycle)
- try_fill()    : all-or-nothing fill, both List[Leg] and Dict[str, Leg] modes
- positions     : Dict[str, Trade] — keyed open trades
- closed_trades : List[Trade]     — full history, never wiped
- max_cycles    : strategy can reset N times per day (default 1)

User subclasses override:
  on_day_start, can_enter, on_entry       (required)
  on_adjust, on_exit_condition, on_exit   (optional, have safe defaults)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from fastbt.backtest.models import Instrument, Leg, Trade

logger = logging.getLogger(__name__)


class Strategy(ABC):
    """
    Abstract base class for all backtesting strategies.

    The engine calls run_one_cycle() each clock tick, which drives the
    IDLE → ACTIVE → DONE state machine. Users implement on_entry, on_adjust,
    and on_exit_condition to express their logic.

    Design principles:
    - State transitions are owned by the engine (try_fill → ACTIVE,
      _handle_cycle_done → IDLE or DONE, _eod_force_close → DONE).
    - positions is a Dict[str, Trade] with meaningful string keys.
    - closed_trades accumulates across ALL days and cycles — never wiped.
    """

    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.engine = None  # injected by BacktestEngine.add_strategy()

        # State machine
        self.state: str = "IDLE"        # "IDLE" | "ACTIVE" | "DONE"
        self.current_cycle: int = 0
        self.max_cycles: int = 1        # overridden by engine from its own config

        # Trade tracking
        self.positions: Dict[str, Trade] = {}     # keyed open trades
        self.closed_trades: List[Trade] = []      # all-time accumulator

    @property
    def open_trades(self) -> List[Trade]:
        """All currently open trades as a list (unordered)."""
        return list(self.positions.values())

    # ─── Leg factory ──────────────────────────────────────────────────────────

    def add(self, strike: int, opt_type: str, side: str, qty: int = 1) -> Leg:
        """
        Create a Leg for use with try_fill().

        Args:
            strike:   Option strike price (e.g., 23600).
            opt_type: "CE" or "PE".
            side:     "BUY" or "SELL".
            qty:      Number of lots (default 1).
        """
        return Leg(instrument=Instrument(strike, opt_type), side=side, qty=qty)

    # ─── Fill mechanics ───────────────────────────────────────────────────────

    def try_fill(
        self,
        legs: Union[List[Leg], Dict[str, Leg]],
        ctx: Any,
    ) -> Optional[Dict[str, Trade]]:
        """
        All-or-nothing fill. Returns a dict of Trade objects keyed by label,
        or None if any leg has a stale or missing price.

        Two input modes:
          List[Leg]       → keys auto-generated from Instrument.key()
          Dict[str, Leg]  → user-provided keys (more readable for complex strategies)

        On success:
          - Trades stored in self.positions under their labels.
          - State transitions from IDLE → ACTIVE (noop if already ACTIVE).

        Raises ValueError:
          - If two legs in the input share the same auto-key (List mode).
          - If any key already exists in self.positions (open position collision).
        """
        # Normalise to Dict[str, Leg]
        if isinstance(legs, list):
            named_legs: Dict[str, Leg] = {}
            for leg in legs:
                key = leg.instrument.key()
                if key in named_legs:
                    raise ValueError(
                        f"Duplicate auto-key '{key}' in try_fill leg list. "
                        "Use Dict mode with unique labels for same-instrument legs."
                    )
                named_legs[key] = leg
        else:
            named_legs = dict(legs)

        # Collision check with existing open positions
        for key in named_legs:
            if key in self.positions:
                raise ValueError(
                    f"Key '{key}' already exists in open positions. "
                    "Close the existing trade first, or use a different label."
                )

        # Check all legs have live price (lag must be 0)
        prices: Dict[str, float] = {}
        for key, leg in named_legs.items():
            price, lag = ctx.get_price(leg.instrument.key())
            if price is None or lag > 0:
                return None  # not all legs live — all-or-nothing
            prices[key] = price

        # All live — create Trade objects
        cost_pct = self.engine.transaction_cost_pct if self.engine else 0.0
        filled: Dict[str, Trade] = {}
        for key, leg in named_legs.items():
            trade = Trade(
                label=key,
                instrument=leg.instrument.key(),
                side=leg.side,
                qty=leg.qty,
                cycle=self.current_cycle,
                entry_tick=ctx.tick,
                entry_index=ctx.tick_index,
                entry_price=prices[key],
            )
            self.positions[key] = trade
            filled[key] = trade

        # IDLE → ACTIVE transition (safe to call from on_adjust too)
        if self.state == "IDLE":
            self.state = "ACTIVE"

        return filled

    def close_trade(
        self,
        label: str,
        tick: Any,
        tick_index: int,
        ctx: Any,
        reason: str = "manual",
    ) -> Optional[Trade]:
        """
        Close an open position by its label.

        Looks up the exit price from ctx.get_price() (fill-forward allowed
        for exits — last known price is the realistic mark). Moves the trade
        from positions → closed_trades and frees the label for reuse.

        Returns:
            The closed Trade, or None if label not found.
        """
        trade = self.positions.pop(label, None)
        if trade is None:
            logger.debug("close_trade: label '%s' not found in positions.", label)
            return None

        # Get current price from context (fill-forward is acceptable for exits)
        price, _ = ctx.get_price(trade.instrument)
        if price is None:
            # No price at all — fall back to entry price (conservative)
            price = trade.entry_price
            logger.warning(
                "close_trade: no price for '%s' at tick '%s'. "
                "Using entry price %.2f as exit price.",
                trade.instrument,
                tick,
                price,
            )

        cost_pct = self.engine.transaction_cost_pct if self.engine else 0.0
        trade.close(
            exit_tick=tick,
            exit_index=tick_index,
            exit_price=price,
            reason=reason,
            transaction_cost_pct=cost_pct,
        )
        self.closed_trades.append(trade)
        return trade

    def close_all(
        self,
        tick: Any,
        tick_index: int,
        ctx: Any,
        reason: str = "close_all",
    ) -> List[Trade]:
        """
        Close all open positions.

        Returns:
            List of closed Trade objects (empty if no open positions).
        """
        closed: List[Trade] = []
        for label in list(self.positions.keys()):
            trade = self.close_trade(label, tick, tick_index, ctx, reason)
            if trade is not None:
                closed.append(trade)
        return closed

    # ─── Lookup helpers ───────────────────────────────────────────────────────

    def get_closed_by_label(self, label: str) -> List[Trade]:
        """Return all closed trades that carried the given label."""
        return [t for t in self.closed_trades if t.label == label]

    def get_closed_by_instrument(self, instrument_key: str) -> List[Trade]:
        """Return all closed trades for the given instrument key (e.g. '23600CE')."""
        return [t for t in self.closed_trades if t.instrument == instrument_key]

    # ─── Engine-driven lifecycle (not overridable) ────────────────────────────

    def run_one_cycle(self, tick: Any, ctx: Any) -> None:
        """
        Called by BacktestEngine once per clock tick.
        Drives the IDLE → ACTIVE → DONE state machine.

        Guaranteed per-tick order:
          IDLE:   can_enter? → on_entry
          ACTIVE: on_adjust → on_exit_condition? → on_exit → _handle_cycle_done
        """
        if self.state == "DONE":
            return

        if self.state == "IDLE":
            if self.can_enter(tick, ctx):
                self.on_entry(tick, ctx)
                # State transition happens inside try_fill() upon successful fill.
                # If on_entry doesn't call try_fill, or try_fill returns None,
                # state stays IDLE and can_enter is checked again next tick.

        elif self.state == "ACTIVE":
            self.on_adjust(tick, ctx)
            if self.on_exit_condition(tick, ctx):
                self.on_exit(tick, ctx)
                self._handle_cycle_done()

    def _handle_cycle_done(self) -> None:
        """
        Called after on_exit() completes.
        Increments the cycle counter or marks the strategy DONE for the day.
        """
        if self.current_cycle < self.max_cycles - 1:
            self.current_cycle += 1
            self.positions.clear()
            self.state = "IDLE"
        else:
            self.state = "DONE"

    def _eod_force_close(self, tick: Any, tick_index: int, ctx: Any) -> None:
        """
        Called by BacktestEngine on the last clock tick — always.

        Closes all remaining open positions and marks state DONE,
        regardless of current state or cycle count.
        """
        self.close_all(tick, tick_index, ctx, reason="EOD_FORCE")
        self.state = "DONE"

    def _reset_for_new_day(self) -> None:
        """
        Called by BacktestEngine before on_day_start() each trading day.

        Resets per-day state. closed_trades is deliberately NOT cleared —
        it accumulates across all days for full backtest reporting.
        """
        self.state = "IDLE"
        self.current_cycle = 0
        self.positions.clear()
        # closed_trades intentionally preserved

    # ─── User-overridable hooks ───────────────────────────────────────────────

    @abstractmethod
    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        """
        Called once per day before the clock loop starts.

        The engine has already loaded NIFTY_SPOT into cache before this fires.
        Use ctx.prefetch() here to warm the cache for known instruments.

        Return False (or omit return) to skip the entire day.
        """

    @abstractmethod
    def can_enter(self, tick: Any, ctx: Any) -> bool:
        """
        Return True when entry conditions are met for this tick.

        Called every tick while state is IDLE. Keep this lightweight.
        Example: return tick >= "09:20:00" and not self.positions
        """

    @abstractmethod
    def on_entry(self, tick: Any, ctx: Any) -> None:
        """
        Called when can_enter() returns True and state is IDLE.

        Call self.try_fill({...}, ctx) here to enter the market.
        If try_fill returns None (prices not live), on_entry will be
        called again automatically next tick — no retry logic needed.
        """

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        """
        Called every tick while state is ACTIVE, before exit check.

        Use for stop-loss monitoring, rolling legs, hedging, partial closes.
        Can call try_fill() to open new legs or close_trade() to close existing ones.
        State remains ACTIVE regardless of what on_adjust does.

        Default: no-op.
        """

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        """
        Return True when the strategy should terminate.

        Called every tick while state is ACTIVE, after on_adjust.
        Return True to trigger on_exit() and _handle_cycle_done().

        Default: always False (strategy never self-terminates — relies on EOD).
        """
        return False

    def on_exit(self, tick: Any, ctx: Any) -> None:
        """
        Called when on_exit_condition() returns True.

        Default: close all open positions.
        Override to implement custom exit logic (e.g. partial close).
        """
        self.close_all(tick, ctx.tick_index, ctx, reason="exit_signal")

    def on_day_end(self, ctx: Any) -> None:
        """
        Called after EOD force close, once per trading day.

        Use for post-day logging or analysis. Default: no-op.
        """
