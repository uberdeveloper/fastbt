"""
Strategy 5: Opening Range Momentum
====================================
Observe the 09:15–09:29 range, then buy ATM CE or PE on the 09:30 breakout.

Rules:
- Range window: track spot high/low from 09:15 → 09:29
- At 09:30: spot > range high → BUY ATM CE (bullish breakout)
            spot < range low  → BUY ATM PE (bearish breakout)
            else              → skip day (no trade)
- Stop  : exit if option loses 50% of entry value
- Target: exit if option doubles (2x entry value)
- Exit  : EOD force-close as backstop

Run:
    uv run python examples/strategies/opening_range_momentum.py
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, List

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
RANGE_END_TIME = "09:29:00"
ENTRY_TIME = "09:30:00"
STOP_PCT = 0.50
TARGET_PCT = 2.00


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    fmt = "%H:%M:%S"
    t = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while t <= stop:
        clock.append(t.strftime(fmt))
        t += timedelta(minutes=1)
    return clock


class OpeningRangeMomentum(Strategy):
    """Buy ATM CE or PE on a 15-minute opening range breakout."""

    def __init__(self) -> None:
        super().__init__(name="OpeningRangeMomentum")
        self._range_high: float = 0.0
        self._range_low: float = float("inf")
        self._entry_price: float = 0.0

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        self._range_high = 0.0
        self._range_low = float("inf")
        self._entry_price = 0.0
        return True

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        """Track opening range until ENTRY_TIME."""
        if ctx.time <= RANGE_END_TIME:
            spot, lag = ctx.get_spot()
            if spot is not None and lag == 0:
                self._range_high = max(self._range_high, spot)
                self._range_low = min(self._range_low, spot)

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time == ENTRY_TIME

    def on_entry(self, tick: Any, ctx: Any) -> None:
        spot, lag = ctx.get_spot()
        if spot is None or lag > 0:
            return

        if spot > self._range_high:
            direction = "CE"
        elif spot < self._range_low:
            direction = "PE"
        else:
            return  # inside range — no trade

        atm = ctx.get_atm(step=50)
        fill = self.try_fill([self.add(atm, direction, "BUY")], ctx)
        if fill:
            self._entry_price = list(fill.values())[0].entry_price

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
        reason = (
            "SL"
            if (price or self._entry_price) <= self._entry_price * STOP_PCT
            else "TARGET"
        )
        self.close_all(tick, ctx.tick_index, ctx, reason=reason)


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = OpeningRangeMomentum()
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
    print("  RANGE    : 09:15–09:29  |  ENTRY: 09:30")
    print("  STOP     : 50%          |  TARGET: 2x")
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

    ce_days = sum(1 for t in strategy.closed_trades if t.instrument.endswith("CE"))
    pe_days = sum(1 for t in strategy.closed_trades if t.instrument.endswith("PE"))
    print(f"\n  Bullish days (CE) : {ce_days}")
    print(f"  Bearish days (PE) : {pe_days}")

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
