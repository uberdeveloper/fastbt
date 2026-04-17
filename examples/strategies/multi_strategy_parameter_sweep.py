"""
Multi-Strategy Parameter Sweep — Short Straddle SL Comparison
==============================================================
Runs the same short-straddle strategy with four different stop-loss
percentages (10%, 15%, 20%, 30%) in a single pass via MultiStrategyEngine.

Why MultiStrategyEngine?
  - Without warmer: 4 × N_days DuckDB calls to prefetch ATM strikes.
  - With    warmer: 1 × N_days DuckDB calls shared across all variants.
  - Lazy-fetched strikes (if any variant goes further OTM): unchanged —
    each strategy fetches independently from its own private cache copy.

Rules (per variant):
  - Entry  : sell ATM CE + PE at ENTRY_TIME (09:20)
  - SL     : close both legs when combined live premium exceeds
             entry_premium × (1 + sl_pct)
  - Exit   : EOD force-close (if SL not triggered)
  - Cycles : 1 entry-exit per day

Run:
    uv run python examples/strategies/multi_strategy_parameter_sweep.py
"""

from typing import Any, List

from fastbt.backtest.context import DayStartContext
from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.models import Instrument
from fastbt.backtest.multi_engine import MultiStrategyEngine
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
START_DATE = "2025-01-01"
END_DATE = "2025-03-31"
ENTRY_TIME = "09:20:00"
ATM_STEP = 50  # NIFTY strikes in 50-point increments
PREFETCH_RANGE = 300  # pre-warm ATM ± 300 points (covers any reasonable SL)


# ── Strategy ──────────────────────────────────────────────────────────────────


class ShortStraddle(Strategy):
    """
    Sell ATM CE + PE at ENTRY_TIME; exit on combined stop-loss or EOD.

    Args:
        sl_pct: Stop-loss expressed as a fraction of entry premium.
                0.20 → exit when combined live premium is 20% above entry.
    """

    def __init__(self, sl_pct: float, **kwargs) -> None:
        super().__init__(**kwargs)
        self.sl_pct = sl_pct
        self._entry_premium: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=ATM_STEP)
        fill = self.try_fill(
            {
                "ce": self.add(atm, "CE", "SELL"),
                "pe": self.add(atm, "PE", "SELL"),
            },
            ctx,
        )
        if fill:
            self._entry_premium = fill["ce"].entry_price + fill["pe"].entry_price

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        if "ce" not in self.positions or "pe" not in self.positions:
            return False
        ce_price, _ = ctx.get_price(self.positions["ce"].instrument)
        pe_price, _ = ctx.get_price(self.positions["pe"].instrument)
        if ce_price is None or pe_price is None:
            return False
        return (ce_price + pe_price) >= self._entry_premium * (1 + self.sl_pct)

    def _reset_for_new_day(self) -> None:
        super()._reset_for_new_day()
        self._entry_premium = 0.0


# ── Cache warmer ──────────────────────────────────────────────────────────────


def warm_atm_range(trade_date: str, ctx: DayStartContext) -> None:
    """
    Pre-load ATM ± PREFETCH_RANGE in ATM_STEP increments — called once per day.

    Each strategy receives a deep-copy of this warmed cache, so no strategy
    triggers an additional DuckDB query for these instruments.  Any instrument
    outside this range is still lazy-fetched per strategy if needed.
    """
    spot = ctx.get_spot()
    atm = round(spot / ATM_STEP) * ATM_STEP
    for offset in range(-PREFETCH_RANGE, PREFETCH_RANGE + ATM_STEP, ATM_STEP):
        ctx.prefetch(Instrument(atm + offset, "CE"))
        ctx.prefetch(Instrument(atm + offset, "PE"))


# ── Run ───────────────────────────────────────────────────────────────────────


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)

    # Create one BacktestEngine per SL variant.
    # All engines share the same DataSource instance — required by MultiStrategyEngine.
    sl_variants: List[float] = [0.10, 0.15, 0.20, 0.30]
    engines = []
    for sl in sl_variants:
        strategy = ShortStraddle(
            sl_pct=sl,
            name=f"straddle_sl{int(sl * 100):02d}pct",
        )
        engine = BacktestEngine(loader, transaction_cost_pct=0.05, max_cycles=1)
        engine.add_strategy(strategy)
        engines.append(engine)

    # Single run; warmer fires once per day; each strategy gets its own cache copy.
    multi = MultiStrategyEngine(engines, cache_warmer=warm_atm_range)
    multi.run(START_DATE, END_DATE)

    # ── Results table ──────────────────────────────────────────────────────────
    sep = "=" * 74
    print(f"\n{sep}")
    print(
        f"  MULTI-STRATEGY SWEEP — Short Straddle, Stop-Loss Comparison\n"
        f"  Period : {START_DATE}  →  {END_DATE}"
    )
    print(sep)
    print(
        f"  {'Strategy':<26} {'Trades':>6} {'Net PnL':>10} "
        f"{'Win%':>6} {'Avg P':>8} {'Avg L':>8} {'MaxDD':>8}"
    )
    print("-" * 74)

    for engine in multi.engines:
        s = engine.strategy
        trades = s.closed_trades

        if not trades:
            print(f"  {s.name:<26} {'0':>6} {'—':>10}")
            continue

        analyzer = PerformanceAnalyzer(trades)
        metrics = analyzer.calculate_all_metrics()

        print(
            f"  {s.name:<26} "
            f"{metrics['total_trades']:>6} "
            f"{metrics['total_pnl']:>10.2f} "
            f"{(metrics['win_rate'] or 0):>5.1f}% "
            f"{(metrics['avg_profit'] or 0):>8.2f} "
            f"{(metrics['avg_loss']   or 0):>8.2f} "
            f"{metrics['max_drawdown']:>8.2f}"
        )

    print(sep)

    # ── Per-strategy exit breakdown ────────────────────────────────────────────
    print("\n  Exit Breakdown by Strategy:")
    print("-" * 74)
    print(f"  {'Strategy':<26} {'SL hits':>8} {'EOD exits':>10} {'Total':>8}")
    print("-" * 74)

    for engine in multi.engines:
        s = engine.strategy
        trades = s.closed_trades
        sl_hits = sum(1 for t in trades if t.exit_reason == "STOP_LOSS")
        eod_exits = sum(1 for t in trades if t.exit_reason == "EOD_FORCE")
        print(f"  {s.name:<26} {sl_hits:>8} {eod_exits:>10} {len(trades):>8}")

    print(sep + "\n")


if __name__ == "__main__":
    run()
