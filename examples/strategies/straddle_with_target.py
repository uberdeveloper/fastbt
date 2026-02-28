"""
Strategy 4: Short Straddle with Profit Target
===============================================
Classic theta-decay play with an explicit take-profit exit.

Rules:
  - User clock  : 09:15 → 15:20 (every minute, stops before the 15:29 rush)
  - Entry       : 09:20, sell ATM CE + PE (auto-generated keys via List[Leg])
  - Take-profit : exit when combined mark reaches ≤ 40% of entry premium
                  (i.e. we've captured 60% of the premium)
  - Hard stop   : exit when combined mark reaches ≥ 180% of entry premium
  - EOD force-close as final backstop

Features demonstrated:
  ✓  User clock (09:15 → 15:20)
  ✓  List[Leg] mode for auto-generated keys ("23600CE", "23600PE")
  ✓  on_exit_condition — two conditions (target + stop)
  ✓  on_exit     — named exit reasons passed to close_all

Run:
    uv run python examples/strategies/straddle_with_target.py
"""

from datetime import datetime, timedelta
from typing import Any, List, Optional

import pandas as pd

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.models import Instrument
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
TARGET_RETAIN_PCT = (
    0.40  # exit when combined value drops to 40% of entry (60% captured)
)
SL_EXPAND_PCT = 1.80  # hard stop when combined value reaches 180% of entry


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    """Generate a 1-minute clock from start to end (inclusive)."""
    fmt = "%H:%M:%S"
    current = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while current <= stop:
        clock.append(current.strftime(fmt))
        current += timedelta(minutes=1)
    return clock


class StraddleWithTarget(Strategy):
    """
    Sell ATM CE + PE at 09:20.

    Uses List[Leg] for auto-key generation — positions will be keyed as
    e.g.  {"23600CE": Trade, "23600PE": Trade}  automatically.

    Dual exit gate:
      - Target: close when combined mark ≤ 40% of entry premium
      - Stop  : close when combined mark ≥ 180% of entry premium
    """

    def __init__(self) -> None:
        super().__init__(name="StraddleWithTarget")
        self._entry_premium: float = 0.0
        self._exit_reason: str = "EOD"

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        atm = ctx.get_atm(step=50)
        ctx.prefetch(Instrument(atm, "CE"))
        ctx.prefetch(Instrument(atm, "PE"))
        return True

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick >= ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)

        # ── List[Leg] mode — keys auto = "23600CE" and "23600PE" ─────────────
        fill = self.try_fill(
            [
                self.add(atm, "CE", "SELL"),
                self.add(atm, "PE", "SELL"),
            ],
            ctx,
        )
        if fill:
            self._entry_premium = sum(t.entry_price for t in fill.values())

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        """Check target and stop on every tick."""
        combined = self._combined_mark(ctx)
        if combined is None:
            return False

        if combined <= self._entry_premium * TARGET_RETAIN_PCT:
            self._exit_reason = "TARGET"
            return True

        if combined >= self._entry_premium * SL_EXPAND_PCT:
            self._exit_reason = "SL"
            return True

        return False

    def on_exit(self, tick: Any, ctx: Any) -> None:
        self.close_all(tick, ctx.tick_index, ctx, reason=self._exit_reason)

    def on_day_end(self, ctx: Any) -> None:
        pass

    # ── Internal helper ────────────────────────────────────────────────────────

    def _combined_mark(self, ctx: Any) -> Optional[float]:
        """Sum of current market prices for all open positions."""
        total = 0.0
        for trade in self.positions.values():
            price, _ = ctx.get_price(trade.instrument)
            if price is None:
                return None
            total += price
        return total


def print_results(strategy: StraddleWithTarget) -> None:
    trades = strategy.closed_trades
    analyzer = PerformanceAnalyzer(trades)
    metrics = analyzer.calculate_all_metrics()

    print("\n" + "=" * 55)
    print(f"  STRATEGY : {strategy.name}")
    print("  PERIOD   : 2025-01-01  →  2025-03-31")
    print("  TARGET   : capture 60% of premium (mark at 40%)")
    print("  STOP     : exit if mark reaches 180% of entry")
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

    from collections import Counter

    reasons = Counter(t.exit_reason for t in trades)
    print("\n  Exit reasons:")
    for reason, count in sorted(reasons.items()):
        print(f"    {reason:<15}: {count}")

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
    strategy = StraddleWithTarget()
    clock = make_clock("09:15:00", "15:20:00")

    engine = BacktestEngine(
        loader,
        transaction_cost_pct=0.05,
        clock=clock,
    )
    engine.add_strategy(strategy)
    engine.run("2025-01-01", "2025-03-31")

    print_results(strategy)


if __name__ == "__main__":
    run()
