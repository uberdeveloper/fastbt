"""
Strategy 2: Short Strangle with Delta-Based Strikes
=====================================================
Sell OTM CE + PE (each ~1 step away from ATM) at 09:20 and hold till EOD.

Rules:
- Entry : 09:20, sell (ATM + 100) CE and (ATM - 100) PE
  The extra 100-point cushion collects less premium but has higher probability.
- Stop-loss : fixed per-leg stop — close ONLY the breached leg
  when it moves 3x vs. its entry price (individual leg SL).
- Exit: EOD force-close (or per-leg stop).

Why strangle vs straddle?
- Lower premium received, but wider breakeven zone.
- Isolating per-leg SL demonstrates the close_trade() API individually.

Run:
    uv run python examples/strategies/short_strangle.py
"""

from typing import Any

import pandas as pd

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.models import Instrument
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
LEG_STEP = 100  # points OTM from ATM (2 strikes away)
LEG_SL_MULTIPLIER = 3.0  # close a leg if its price triples vs. entry


class ShortStrangle(Strategy):
    """
    Sell OTM CE at ATM+100 and OTM PE at ATM-100.

    Per-leg stop: close whichever leg moves 3× vs. its entry price.
    Remaining open leg is force-closed at EOD.
    """

    def __init__(self):
        super().__init__(name="ShortStrangle")

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        atm = ctx.get_atm(step=50)
        ctx.prefetch(Instrument(atm + LEG_STEP, "CE"))
        ctx.prefetch(Instrument(atm - LEG_STEP, "PE"))
        return True

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick >= ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        ce_strike = atm + LEG_STEP
        pe_strike = atm - LEG_STEP
        self.try_fill(
            {
                "ce": self.add(ce_strike, "CE", "SELL"),
                "pe": self.add(pe_strike, "PE", "SELL"),
            },
            ctx,
        )

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        """Per-leg stop-loss: close only the leg that has hit its stop."""
        for label in list(self.positions.keys()):
            trade = self.positions[label]
            current_price, lag = ctx.get_price(trade.instrument)
            if current_price is None or lag > 0:
                continue
            # For a SELL trade, pain increases when price rises
            if current_price >= trade.entry_price * LEG_SL_MULTIPLIER:
                self.close_trade(label, tick, ctx.tick_index, ctx, reason="LEG_SL")

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        # Only self-exit when BOTH legs are gone (both hit SL)
        return bool(not self.positions)

    def on_exit(self, tick: Any, ctx: Any) -> None:
        # Both legs already closed by on_adjust SL; nothing extra needed
        pass

    def on_day_end(self, ctx: Any) -> None:
        pass


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStrangle()
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

    # Show legs that hit stop-loss
    sl_trades = [t for t in trades if t.exit_reason == "LEG_SL"]
    eod_trades = [t for t in trades if t.exit_reason == "EOD_FORCE"]
    print(f"\n  Legs stopped out  : {len(sl_trades)}")
    print(f"  Legs EOD-closed   : {len(eod_trades)}")

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


if __name__ == "__main__":
    run()
