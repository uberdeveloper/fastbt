"""
Strategy: ATM Short Strangle — using relative strike mode
==========================================================
Demonstrates relative_strikes=True and strike_step class variables.

Sells 1-step OTM CE + PE at 09:20 and holds till EOD.

Rules:
- Entry: 09:20, sell 1 OTM call + 1 OTM put
- strike=1 on CE → atm + 1*step (above ATM)
- strike=1 on PE → atm - 1*step (below ATM)
- Stop-loss: close both legs if combined premium doubles
- Exit: EOD force-close (or stop-loss)

Compare with short_straddle.py — notice on_entry is much cleaner:
no manual ATM computation, no Instrument imports needed.

Run:
    uv run python examples/strategies/short_strangle_relative.py
"""

from typing import Any

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
SL_MULTIPLIER = 2.0


class ShortStrangleRelative(Strategy):
    """
    Sell 1-step OTM CE + PE at 09:20 using relative strike mode.

    relative_strikes = True  — strike values in add() are offsets from ATM.
    strike_step = 50         — Nifty step size; change to 100 for BankNifty.
    """

    relative_strikes = True
    strike_step = 50

    def __init__(self):
        super().__init__(name="ShortStrangleRelative")
        self._entry_premium: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        # strike=1 means 1 step OTM for each leg — direction is inferred from opt_type
        fill = self.try_fill(
            {
                "ce": self.add(1, "CE", "SELL"),
                "pe": self.add(1, "PE", "SELL"),
            },
            ctx,
        )
        if fill:
            self._entry_premium = fill["ce"].entry_price + fill["pe"].entry_price

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        if not self.positions:
            return
        ce_price, _ = ctx.get_price(self.positions["ce"].instrument)
        pe_price, _ = ctx.get_price(self.positions["pe"].instrument)
        if ce_price is None or pe_price is None:
            return
        if ce_price + pe_price >= self._entry_premium * SL_MULTIPLIER:
            self.close_all(tick, ctx.tick_index, ctx, reason="SL")

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        return bool(not self.positions)

    def on_exit(self, tick: Any, ctx: Any) -> None:
        pass


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStrangleRelative()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(strategy)
    engine.run("2025-01-01", "2025-03-31")

    trades = strategy.closed_trades
    analyzer = PerformanceAnalyzer(trades)
    metrics = analyzer.calculate_all_metrics()

    print("\n" + "=" * 55)
    print(f"  STRATEGY : {strategy.name}")
    print("  PERIOD   : 2025-01-01  →  2025-03-31")
    print("=" * 55)
    print(f"  Total trades      : {metrics['total_trades']}")
    print(f"  Total PnL         : {metrics['total_pnl']:>10.2f}")
    print(
        f"  Win rate          : {metrics['win_rate']:.1f}%"
        if metrics["win_rate"] is not None
        else "  Win rate          : N/A"
    )
    print(
        f"  Avg profit        : {metrics['avg_profit']:.2f}"
        if metrics["avg_profit"] is not None
        else "  Avg profit        : N/A"
    )
    print(
        f"  Avg loss          : {metrics['avg_loss']:.2f}"
        if metrics["avg_loss"] is not None
        else "  Avg loss          : N/A"
    )
    print(f"  Max drawdown      : {metrics['max_drawdown']:.2f}")
    print(
        f"  Sharpe (trade-lv) : {metrics['sharpe_ratio']:.3f}"
        if metrics["sharpe_ratio"] is not None
        else "  Sharpe            : N/A"
    )
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


if __name__ == "__main__":
    run()
