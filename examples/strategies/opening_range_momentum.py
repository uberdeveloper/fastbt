"""
Strategy 5: Opening Range Momentum (Directional)
=================================================
Wait for the first 15 minutes (09:15–09:30) to form a range.
Then buy the option in the direction of the breakout.

Rules:
  - User clock: 09:15 → 15:20
  - Observe range: track high and low of spot from 09:15 → 09:29
  - At 09:30: if spot > range high → BUY ATM CE (bullish breakout)
              if spot < range low  → BUY ATM PE (bearish breakout)
              else                 → skip the day (no trade)
  - Single leg, LONG (BUY) — profit when the move continues
  - Hard stop: 50% loss on the option (cut if option halves in value)
  - Target    : 100% gain on the option (double-up and exit)
  - EOD force-close as backstop

Features demonstrated:
  ✓  User clock (09:15 → 15:20)
  ✓  on_day_start — resets per-day state (_range_high/_range_low).
     NOTE: the engine resets positions/state automatically, but custom
     instance variables like these must be reset manually here.
  ✓  on_day_start returning False to skip a day gracefully
  ✓  List[Leg] auto-keys (single leg — key = "23600CE" or "23600PE")
  ✓  BUY side option trade (not just selling premium)

Run:
    uv run python examples/strategies/opening_range_momentum.py
"""

from typing import Any, Optional

import pandas as pd

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy
from examples.strategies._utils import make_clock

DATA_PATH = "/home/pi/data/q1_2025.parquet"
RANGE_END_TIME = "09:29:00"  # last tick of the opening range window
ENTRY_TIME = "09:30:00"  # breakout assessment tick
STOP_PCT = 0.50  # exit if option loses 50% of entry value
TARGET_PCT = 2.00  # exit if option doubles (200% of entry value)


class OpeningRangeMomentum(Strategy):
    """
    Buy ATM CE or PE on a 15-minute opening range breakout.

    The chosen option is stored as a single-leg position with an
    auto-generated key (e.g. "23600CE").

    on_day_start is required here — not for prefetch, but to reset
    _range_high/_range_low before each day's clock loop begins.
    It also returns False on no-signal days to skip the loop entirely.
    """

    def __init__(self) -> None:
        super().__init__(name="OpeningRangeMomentum")
        self._range_high: float = 0.0
        self._range_low: float = float("inf")
        self._direction: Optional[str] = None  # "CE" or "PE"
        self._entry_price: float = 0.0

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        # Reset per-day range state — the engine does NOT reset custom attributes.
        self._range_high = 0.0
        self._range_low = float("inf")
        self._direction = None
        self._entry_price = 0.0
        return True  # always run; range is observed during the clock loop

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick == ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        """Assess breakout direction and enter if signal exists."""
        spot, lag = ctx.get_spot()
        if spot is None or lag > 0:
            return  # no live spot — skip

        if spot > self._range_high:
            direction = "CE"  # bullish breakout → buy call
        elif spot < self._range_low:
            direction = "PE"  # bearish breakout → buy put
        else:
            return  # inside range → no trade today

        atm = ctx.get_atm(step=50)
        # Single leg via List mode — key auto-set to e.g. "23600CE"
        fill = self.try_fill([self.add(atm, direction, "BUY")], ctx)
        if fill:
            self._entry_price = list(fill.values())[0].entry_price
            self._direction = direction

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        """Update the opening range while still in the observation window."""
        if tick <= RANGE_END_TIME:
            spot, lag = ctx.get_spot()
            if spot is not None and lag == 0:
                self._range_high = max(self._range_high, spot)
                self._range_low = min(self._range_low, spot)

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        if not self.positions:
            return False
        trade = list(self.positions.values())[0]
        price, _ = ctx.get_price(trade.instrument)
        if price is None:
            return False
        return (
            price <= self._entry_price * STOP_PCT
            or price >= self._entry_price * TARGET_PCT
        )

    def on_exit(self, tick: Any, ctx: Any) -> None:
        trade = list(self.positions.values())[0]
        price, _ = ctx.get_price(trade.instrument)
        if price is None:
            price = trade.entry_price
        reason = "SL_50PCT" if price <= self._entry_price * STOP_PCT else "TARGET_2X"
        self.close_all(tick, ctx.tick_index, ctx, reason=reason)


def print_results(strategy: OpeningRangeMomentum) -> None:
    from collections import Counter

    trades = strategy.closed_trades
    analyzer = PerformanceAnalyzer(trades)
    metrics = analyzer.calculate_all_metrics()

    print("\n" + "=" * 55)
    print(f"  STRATEGY : {strategy.name}")
    print("  PERIOD   : 2025-01-01  →  2025-03-31")
    print("  RANGE    : 09:15 → 09:29  |  ENTRY: 09:30")
    print("  STOP     : 50% of entry   |  TARGET: 2× entry")
    print("  CLOCK    : 09:15 → 15:20 (user-defined, 1-min)")
    print("=" * 55)
    print(f"  Total trades      : {metrics['total_trades']}")
    print(f"  Total PnL         : {metrics['total_pnl']:>10.2f}")
    if metrics["win_rate"] is not None:
        print(f"  Win rate          : {metrics['win_rate']:.1f}%")
    if metrics["avg_profit"] is not None:
        print(f"  Avg profit        : {metrics['avg_profit']:.2f}")
    if metrics["avg_loss"] is not None:
        print(f"  Avg loss          : {metrics['avg_loss']:.2f}")
    print(f"  Max drawdown      : {metrics['max_drawdown']:.2f}")
    if metrics["sharpe_ratio"] is not None:
        print(f"  Sharpe (trade-lv) : {metrics['sharpe_ratio']:.3f}")
    print("=" * 55)

    reasons = Counter(t.exit_reason for t in trades)
    print("\n  Exit reasons:")
    for reason, count in sorted(reasons.items()):
        print(f"    {reason:<15}: {count}")

    ce_count = sum(1 for t in trades if t.instrument.endswith("CE"))
    pe_count = sum(1 for t in trades if t.instrument.endswith("PE"))
    print(f"\n  Bullish days (CE bought) : {ce_count}")
    print(f"  Bearish days (PE bought) : {pe_count}")
    print(f"  No-signal days (skipped) : {61 - ce_count - pe_count}")

    if trades:
        rows = [t.to_dict() for t in trades]
        df = pd.DataFrame(rows)[
            [
                "label",
                "instrument",
                "side",
                "entry_tick",
                "entry_price",
                "exit_tick",
                "exit_price",
                "exit_reason",
                "net_pnl",
            ]
        ]
        print("\nTrade log (first 20 rows):")
        print(df.head(20).to_string(index=False))


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = OpeningRangeMomentum()
    clock = make_clock("09:15:00", "15:20:00")
    engine = BacktestEngine(loader, transaction_cost_pct=0.05, clock=clock)
    engine.add_strategy(strategy)
    engine.run("2025-01-01", "2025-03-31")
    print_results(strategy)


if __name__ == "__main__":
    run()
