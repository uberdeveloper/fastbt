"""
Strategy 2: Short Strangle with Per-Leg Stop
=============================================
Sell OTM CE + PE (ATM ± 100) at 09:20 and hold till EOD.

Rules:
- Entry: 09:20, sell (ATM+100) CE and (ATM-100) PE
- Per-leg stop: close only the breached leg when it triples vs. entry
- Exit: EOD force-close (or per-leg stop)

Run:
    uv run python examples/strategies/short_strangle.py
"""

from typing import Any

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
LEG_STEP = 100
LEG_SL_MULTIPLIER = 3.0


class ShortStrangle(Strategy):
    """Sell OTM strangle at 09:20. Per-leg SL at 3x entry price."""

    def __init__(self):
        super().__init__(name="ShortStrangle")

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        self.try_fill(
            {
                "ce": self.add(atm + LEG_STEP, "CE", "SELL"),
                "pe": self.add(atm - LEG_STEP, "PE", "SELL"),
            },
            ctx,
        )

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        """Close only the leg that hit its stop."""
        for label in list(self.positions.keys()):
            trade = self.positions[label]
            price, _ = ctx.get_price(trade.instrument)
            if price is not None and price >= trade.entry_price * LEG_SL_MULTIPLIER:
                self.close_trade(label, tick, ctx.tick_index, ctx, reason="LEG_SL")


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStrangle()
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

    sl_trades = [t for t in strategy.closed_trades if t.exit_reason == "LEG_SL"]
    print(f"\n  Legs stopped out  : {len(sl_trades)}")

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
