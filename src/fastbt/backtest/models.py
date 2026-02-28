"""
fastbt.backtest.models
======================
Core data classes for the FastBT backtesting engine.

- Instrument : immutable option contract identifier (strike + opt_type)
- Leg        : single order leg, input to Strategy.try_fill()
- Trade      : filled trade with PnL tracking, created by try_fill()
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Instrument:
    """
    Immutable identifier for a single option contract.

    Frozen so it is hashable and safe to use as a dict key.
    Phase 2: add expiry: Optional[str] = None, key becomes '23600CE_20250130'.
    """

    strike: int
    opt_type: str  # "CE" or "PE"

    def key(self) -> str:
        """Return the cache-key string, e.g. '23600CE'."""
        return f"{self.strike}{self.opt_type}"

    def __repr__(self) -> str:
        return self.key()


@dataclass
class Leg:
    """
    A single leg of a multi-leg order — input to Strategy.try_fill().

    The dict key provided to try_fill() is used as the trade label.
    Default qty=1.
    """

    instrument: Instrument
    side: str  # "BUY" or "SELL"
    qty: int = 1


@dataclass
class Trade:
    """
    Represents a single filled trade.

    Created by Strategy.try_fill() on a successful all-or-nothing fill.
    Closed by Strategy.close_trade() or engine EOD force-close.

    Timing fields use tick_index (absolute counter) for universal slippage
    measurement that works regardless of clock type (timestamps, integers, etc.).
    """

    # Identity
    label: str  # key in strategy.positions ("23600CE" or user label)
    instrument: str  # Instrument.key(), e.g. "23600CE"
    side: str  # "BUY" or "SELL"
    qty: int
    cycle: int  # which max_cycles iteration this belongs to (0-indexed)

    # Entry timing — both clock value and absolute counter
    entry_tick: Any  # clock value when filled (str, int, datetime, ...)
    entry_index: int  # tick_index when filled (absolute counter)
    entry_price: float

    # Exit (populated by Trade.close())
    exit_tick: Any = None
    exit_index: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # PnL (populated by Trade.close())
    gross_pnl: float = 0.0
    transaction_cost: float = 0.0
    net_pnl: float = 0.0

    # Flexible per-trade metadata (e.g. {"tag": "straddle_ce"})
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_open(self) -> bool:
        """True if the trade has not been closed yet."""
        return self.exit_tick is None

    def close(
        self,
        exit_tick: Any,
        exit_index: int,
        exit_price: float,
        reason: str,
        transaction_cost_pct: float = 0.0,
    ) -> None:
        """
        Close the trade and compute gross/net PnL.

        Args:
            exit_tick:            Clock value at exit.
            exit_index:           Tick index (absolute counter) at exit.
            exit_price:           Fill price at exit.
            reason:               Why exited ("SL", "target", "EOD_FORCE", ...).
            transaction_cost_pct: Round-trip cost as % of notional per leg.
                                  E.g. 0.1 means 0.1% per leg (entry + exit).
        """
        self.exit_tick = exit_tick
        self.exit_index = exit_index
        self.exit_price = exit_price
        self.exit_reason = reason

        # SELL profits when price falls; BUY profits when price rises
        multiplier = 1 if self.side == "BUY" else -1
        self.gross_pnl = (self.exit_price - self.entry_price) * self.qty * multiplier

        if transaction_cost_pct > 0:
            entry_cost = abs(self.entry_price * self.qty * transaction_cost_pct / 100)
            exit_cost = abs(self.exit_price * self.qty * transaction_cost_pct / 100)
            self.transaction_cost = entry_cost + exit_cost

        self.net_pnl = self.gross_pnl - self.transaction_cost

    def to_dict(self) -> Dict[str, Any]:
        """
        Flatten trade to a plain dict for DataFrame conversion / reporting.
        metadata keys are merged into the top level.
        """
        return {
            "label": self.label,
            "instrument": self.instrument,
            "side": self.side,
            "qty": self.qty,
            "cycle": self.cycle,
            "entry_tick": self.entry_tick,
            "entry_index": self.entry_index,
            "entry_price": self.entry_price,
            "exit_tick": self.exit_tick,
            "exit_index": self.exit_index,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "gross_pnl": self.gross_pnl,
            "transaction_cost": self.transaction_cost,
            "net_pnl": self.net_pnl,
            **self.metadata,
        }
