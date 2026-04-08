"""
Strategy 3: Iron Condor
========================
Sell OTM strangle + buy further-OTM wings. Exit at 50% profit target.

Structure (4 legs):
  SELL  (ATM+100) CE   short call
  BUY   (ATM+200) CE   long call wing
  SELL  (ATM-100) PE   short put
  BUY   (ATM-200) PE   long put wing

Rules:
- Entry: 09:20, all 4 legs via List[Leg] (keys auto-set to instrument names)
- Target: exit when unrealised PnL >= 50% of net credit collected
- Exit: EOD force-close as backstop

Run:
    uv run python examples/strategies/iron_condor.py
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
WING_STEP = 100
HEDGE_STEP = 200
TARGET_PCT = 0.50


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    fmt = "%H:%M:%S"
    t = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while t <= stop:
        clock.append(t.strftime(fmt))
        t += timedelta(minutes=1)
    return clock


class IronCondor(Strategy):
    """4-leg iron condor with 50% profit target."""

    def __init__(self) -> None:
        super().__init__(name="IronCondor")
        self._max_credit: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        # List[Leg] mode: keys auto-generated from instrument names
        fill = self.try_fill(
            [
                self.add(atm + WING_STEP, "CE", "SELL"),
                self.add(atm + HEDGE_STEP, "CE", "BUY"),
                self.add(atm - WING_STEP, "PE", "SELL"),
                self.add(atm - HEDGE_STEP, "PE", "BUY"),
            ],
            ctx,
        )
        if fill:
            self._max_credit = max(
                sum(
                    t.entry_price if t.side == "SELL" else -t.entry_price
                    for t in fill.values()
                ),
                0.0,
            )

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        if self._max_credit == 0.0:
            return False
        pnl = self._current_pnl(ctx)
        return pnl is not None and pnl >= self._max_credit * TARGET_PCT

    def on_exit(self, tick: Any, ctx: Any) -> None:
        self.close_all(tick, ctx.tick_index, ctx, reason="TARGET")

    def _current_pnl(self, ctx: Any) -> Optional[float]:
        total = 0.0
        for trade in self.positions.values():
            price, _ = ctx.get_price(trade.instrument)
            if price is None:
                return None
            mult = 1 if trade.side == "SELL" else -1
            total += (trade.entry_price - price) * trade.qty * mult
        return total


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = IronCondor()
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
