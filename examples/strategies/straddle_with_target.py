"""
Strategy 4: Short Straddle with Profit Target
===============================================
Sell ATM CE + PE at 09:20. Exit on target or stop, else EOD.

Rules:
- Entry: 09:20, sell ATM CE + PE (List[Leg] mode — keys auto-set to "23600CE" etc.)
- Target: exit when combined mark reaches ≤ 40% of entry (60% captured)
- Stop  : exit when combined mark reaches ≥ 180% of entry
- Exit  : EOD force-close as backstop

Run:
    uv run python examples/strategies/straddle_with_target.py
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
TARGET_PCT = 0.40  # exit when mark decays to 40% of entry (60% captured)
SL_PCT = 1.80  # hard stop at 180% of entry


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    fmt = "%H:%M:%S"
    t = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while t <= stop:
        clock.append(t.strftime(fmt))
        t += timedelta(minutes=1)
    return clock


class StraddleWithTarget(Strategy):
    """Sell ATM straddle at 09:20 with profit target and hard stop."""

    def __init__(self) -> None:
        super().__init__(name="StraddleWithTarget")
        self._entry_premium: float = 0.0
        self._exit_reason: str = "EOD"

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        # List[Leg] mode: keys auto-generated as "23600CE", "23600PE", etc.
        fill = self.try_fill(
            [self.add(atm, "CE", "SELL"), self.add(atm, "PE", "SELL")],
            ctx,
        )
        if fill:
            self._entry_premium = sum(t.entry_price for t in fill.values())

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        mark = self._combined_mark(ctx)
        if mark is None:
            return False
        if mark <= self._entry_premium * TARGET_PCT:
            self._exit_reason = "TARGET"
            return True
        if mark >= self._entry_premium * SL_PCT:
            self._exit_reason = "SL"
            return True
        return False

    def on_exit(self, tick: Any, ctx: Any) -> None:
        self.close_all(tick, ctx.tick_index, ctx, reason=self._exit_reason)

    def _combined_mark(self, ctx: Any) -> Optional[float]:
        total = 0.0
        for trade in self.positions.values():
            price, _ = ctx.get_price(trade.instrument)
            if price is None:
                return None
            total += price
        return total


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = StraddleWithTarget()
    engine = BacktestEngine(
        loader,
        transaction_cost_pct=0.05,
        clock=make_clock("09:15:00", "15:20:00"),
    )
    engine.add_strategy(strategy)
    engine.run("2025-01-01", "2025-03-31")

    analyzer = PerformanceAnalyzer(strategy.closed_trades)
    metrics = analyzer.calculate_all_metrics()

    print("\n" + "=" * 55)
    print(f"  STRATEGY : {strategy.name}")
    print("  PERIOD   : 2025-01-01  →  2025-03-31")
    print("  TARGET   : capture 60% of premium  |  STOP: 180%")
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

    reasons = Counter(t.exit_reason for t in strategy.closed_trades)
    print("\n  Exit reasons:")
    for reason, count in sorted(reasons.items()):
        print(f"    {reason:<15}: {count}")

    df = strategy.to_dataframe()
    cols = [
        "label",
        "instrument",
        "side",
        "entry_tick",
        "entry_price",
        "exit_tick",
        "exit_price",
        "exit_reason",
        "net_pnl",
        "is_open",
    ]
    if not df.empty:
        print("\nTrade log (first 20 rows):")
        print(df[cols].head(20).to_string(index=False))

    # strategy.save_trades("trades.parquet")
    # strategy.save_trades("trades.csv")


if __name__ == "__main__":
    run()
