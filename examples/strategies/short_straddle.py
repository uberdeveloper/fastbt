"""
Strategy 1: ATM Short Straddle
================================
Sell ATM CE + PE at 09:20 and hold till EOD.

Rules:
- Entry: 09:20, sell ATM CE + PE
- Stop-loss: close both legs if combined premium doubles (2x entry)
- Exit: EOD force-close (or stop-loss)

Run:
    uv run python examples/strategies/short_straddle.py
"""

from typing import Any

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
SL_MULTIPLIER = 2.0


class ShortStraddle(Strategy):
    """Sell ATM CE + PE at 09:20. SL when combined premium doubles."""

    def __init__(self):
        super().__init__(name="ShortStraddle")
        self._entry_premium: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        fill = self.try_fill(
            {"ce": self.add(atm, "CE", "SELL"), "pe": self.add(atm, "PE", "SELL")},
            ctx,
        )
        if fill:
            self._entry_premium = fill["ce"].entry_price + fill["pe"].entry_price

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        ce_price, _ = ctx.get_price(self.positions["ce"].instrument)
        pe_price, _ = ctx.get_price(self.positions["pe"].instrument)
        if ce_price is None or pe_price is None:
            return False
        return (ce_price + pe_price) >= self._entry_premium * SL_MULTIPLIER


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStraddle()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
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
