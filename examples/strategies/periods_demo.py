"""
Advanced: Running with Different Holding Periods
=================================================
The same strategy logic can run intraday, multi-day, or till expiry
by changing a single engine parameter: `period`.

  period="day"     (default) — intraday, EOD force-close every day
  period="expiry"            — hold till next expiry; positions carry overnight
  period=5                   — hold for 5 trading days (or any int)

The strategy code does NOT change — only the engine's period argument.

When period > 1 day, tick keys become full datetime strings:
  "2025-01-02 09:20:00" instead of "09:20:00"
The strategy sees these as opaque tick values; ctx.time still returns
the time portion for comparisons like ctx.time >= "09:20:00".

Examples in this file:
  run_intraday()     — classic intraday straddle, exit same day
  run_till_expiry()  — enter on Monday, hold till Thursday expiry
  run_n_days(n)      — hold for N trading days (e.g. weekly positional)

Run:
    uv run python examples/strategies/periods_demo.py
"""

from typing import Any

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
START = "2025-01-01"
END = "2025-03-31"
ENTRY_TIME = "09:20:00"
SL_MULTIPLIER = 2.0


class ShortStraddle(Strategy):
    """
    Sell ATM CE + PE at 09:20. SL when combined premium doubles.

    Works unchanged across all period modes — the engine controls
    when the period ends and the EOD force-close fires.
    """

    def __init__(self, name: str = "ShortStraddle"):
        super().__init__(name=name)
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


def print_results(strategy: ShortStraddle) -> None:
    analyzer = PerformanceAnalyzer(strategy.closed_trades)
    metrics = analyzer.calculate_all_metrics()
    print(f"  Total trades : {metrics['total_trades']}")
    print(f"  Total PnL    : {metrics['total_pnl']:>10.2f}")
    if metrics["win_rate"] is not None:
        print(f"  Win rate     : {metrics['win_rate']:.1f}%")
    print(f"  Max drawdown : {metrics['max_drawdown']:.2f}")


def run_intraday() -> None:
    """
    period="day" (default) — enter at 09:20, exit same day.
    EOD force-close fires at the last tick of each trading day.
    """
    print("\n" + "=" * 55)
    print("  MODE: Intraday  (period='day')")
    print("=" * 55)

    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStraddle(name="Intraday")
    engine = BacktestEngine(loader, transaction_cost_pct=0.05, period="day")
    engine.add_strategy(strategy)
    engine.run(START, END)
    print_results(strategy)


def run_till_expiry() -> None:
    """
    period="expiry" — all days up to the next weekly expiry form one period.
    Positions entered on Monday carry overnight until Thursday (expiry day).
    EOD force-close fires only at the last tick of the expiry day.

    Useful for: theta strategies held for the full expiry week.
    """
    print("\n" + "=" * 55)
    print("  MODE: Till expiry  (period='expiry')")
    print("=" * 55)

    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStraddle(name="TillExpiry")
    engine = BacktestEngine(loader, transaction_cost_pct=0.05, period="expiry")
    engine.add_strategy(strategy)
    engine.run(START, END)
    print_results(strategy)


def run_n_days(n: int = 5) -> None:
    """
    period=n (int) — groups n consecutive trading days into one period.
    Useful for fixed-duration positional trades (e.g. weekly holds).
    EOD force-close fires at the last tick of the nth day.

    Useful for: fixed-duration holds regardless of expiry calendar.
    """
    print("\n" + "=" * 55)
    print(f"  MODE: {n}-day hold  (period={n})")
    print("=" * 55)

    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = ShortStraddle(name=f"{n}DayHold")
    engine = BacktestEngine(loader, transaction_cost_pct=0.05, period=n)
    engine.add_strategy(strategy)
    engine.run(START, END)
    print_results(strategy)


if __name__ == "__main__":
    run_intraday()
    run_till_expiry()
    run_n_days(5)
