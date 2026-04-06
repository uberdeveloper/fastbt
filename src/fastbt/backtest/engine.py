"""
fastbt.backtest.engine
======================
BacktestEngine — orchestrates the clock loop, context management,
and per-period strategy lifecycle.

Per-period sequence (enforced, non-negotiable):
  1. cache.clear()
  2. Load NIFTY_SPOT into cache
  3. strategy._reset_for_new_day()
  4. strategy.on_day_start(date, day_ctx) → may return False to skip
  5. Clock loop: for tick in clock:
       bar_ctx.advance(tick, idx)
       strategy.run_one_cycle(tick, bar_ctx)
  6. strategy._eod_force_close(last_tick, bar_ctx)
  7. strategy.on_day_end(bar_ctx)
"""

import logging
from typing import Any, Dict, List, Optional, Union

from fastbt.backtest.context import BarContext, DayStartContext
from fastbt.backtest.data import DataSource
from fastbt.backtest.strategy import Strategy

logger = logging.getLogger(__name__)


def group_by_day(dates: List[str]) -> List[List[str]]:
    """Each date is its own period. Default behavior."""
    return [[d] for d in dates]


def group_by_n_days(dates: List[str], n: int) -> List[List[str]]:
    """Chunk dates into groups of n. Last group may be smaller."""
    return [dates[i : i + n] for i in range(0, len(dates), n)]


def group_by_expiry(dates: List[str], data_source: DataSource) -> List[List[str]]:
    """Group dates by their nearest expiry from the data source.

    Only considers expiries on or after the trade date (expired contracts
    are excluded). Uses min() on the filtered list so the nearest valid
    expiry is selected regardless of sort order from the DataSource.
    Falls back to the trade date itself if no valid expiry exists.
    """
    groups: dict = {}
    for d in dates:
        expiries = data_source.get_expiries(d)
        valid = [e for e in expiries if e >= d]
        nearest = min(valid) if valid else d
        groups.setdefault(nearest, []).append(d)
    return list(groups.values())


class BacktestEngine:
    """
    Orchestrates a single-strategy backtest over a date range.

    Responsibilities:
    - Iterate over trading days provided by the DataSource
    - Group dates into periods (day, N-days, or expiry-based)
    - Manage a shared cache (clear + reload each period)
    - Drive the strategy lifecycle via run_one_cycle / EOD force close
    - Pass transaction_cost_pct and max_cycles through to the strategy

    Not responsible for:
    - PnL calculation (Strategy / Trade handle this)
    - Performance metrics (PerformanceAnalyzer handles this)
    """

    def __init__(
        self,
        data_source: DataSource,
        transaction_cost_pct: float = 0.0,
        max_cycles: int = 1,
        clock: Optional[List[Any]] = None,
        period: Union[str, int] = "day",
    ):
        """
        Args:
            data_source:          DataSource implementation (DuckDBParquetLoader).
            transaction_cost_pct: Round-trip cost as % of notional, passed to Trade.close().
            max_cycles:           How many entry-exit cycles the strategy may do per day.
            clock:                Optional list of tick values. If None, auto-derived
                                  from NIFTY_SPOT keys (underlying timestamps).
            period:               Grouping mode: "day" (default), "expiry", or int (N days).
        """
        self.data_source = data_source
        self.transaction_cost_pct = transaction_cost_pct
        self.max_cycles = max_cycles
        self.user_clock = clock
        self.period = period
        self.strategy: Optional[Strategy] = None
        self._cache: Dict = {}

    def add_strategy(self, strategy: Strategy) -> None:
        """
        Register a strategy with the engine.

        Injects engine reference and propagates max_cycles so the strategy
        can track cycle count correctly.
        """
        strategy.engine = self
        strategy.max_cycles = self.max_cycles
        self.strategy = strategy

    def run(self, start_date: str, end_date: str) -> None:
        """
        Run the backtest for all trading days in [start_date, end_date].

        Args:
            start_date: First day to include, e.g. "2025-01-02".
            end_date:   Last day to include, e.g. "2025-03-31".
        """
        if self.strategy is None:
            raise ValueError(
                "No strategy registered. Call add_strategy() before run()."
            )

        all_dates = self.data_source.get_available_dates()
        trading_days = [d for d in all_dates if start_date <= d <= end_date]

        # Group dates into periods
        if self.period == "day":
            periods = group_by_day(trading_days)
        elif self.period == "expiry":
            periods = group_by_expiry(trading_days, self.data_source)
        elif isinstance(self.period, int):
            periods = group_by_n_days(trading_days, self.period)
        else:
            raise ValueError(
                f"Invalid period: {self.period!r}. "
                "Use 'day', 'expiry', or an integer."
            )

        logger.info(
            "BacktestEngine: running %d periods (%d days) [%s -> %s]",
            len(periods),
            len(trading_days),
            start_date,
            end_date,
        )

        for period_dates in periods:
            self._run_period(period_dates)

    def _run_period(self, period_dates: List[str]) -> None:
        """
        Execute the full per-period lifecycle for one or more trading dates.

        All steps are mandatory and execute in a fixed, documented order.
        """
        multi_day = len(period_dates) > 1

        # ── 1. Clear cache ────────────────────────────────────────────────────
        self._cache.clear()

        # ── 2. Load underlying for all dates in this period ───────────────────
        merged_underlying: Dict[str, float] = {}
        for d in period_dates:
            daily = self.data_source.get_underlying_data(d)
            for time_key, price in daily.items():
                key = f"{d} {time_key}" if multi_day else time_key
                merged_underlying[key] = price
        self._cache["NIFTY_SPOT"] = merged_underlying

        # ── 3. Derive or use clock ────────────────────────────────────────────
        clock = (
            self.user_clock
            if self.user_clock is not None
            else list(self._cache["NIFTY_SPOT"].keys())
        )

        if not clock:
            logger.warning(
                "No clock ticks for period %s (underlying data empty). Skipping.",
                period_dates,
            )
            return

        # ── 4. Reset strategy per-period state ────────────────────────────────
        self.strategy._reset_for_new_day()
        self.strategy.trade_date = period_dates[0]

        # ── 5. Create contexts ─────────────────────────────────────────────────
        day_ctx = DayStartContext(
            period_dates[0],
            self._cache,
            self.data_source,
            period_dates=period_dates,
        )
        bar_ctx = BarContext(
            self._cache,
            self.data_source,
            period_dates[0],
            clock,
            period_dates=period_dates,
        )

        # ── 6. on_day_start — user can prefetch and bail ──────────────────────
        should_run = self.strategy.on_day_start(period_dates[0], day_ctx)
        if should_run is False:
            logger.info(
                "Strategy skipped period %s (on_day_start returned False).",
                period_dates,
            )
            return

        # ── 7. Clock loop ─────────────────────────────────────────────────────
        for tick_index, tick in enumerate(clock):
            bar_ctx.advance(tick, tick_index)
            self.strategy.run_one_cycle(tick, bar_ctx)

        # ── 8. EOD force close — always fires at period end ───────────────────
        last_tick = clock[-1]
        last_index = len(clock) - 1
        bar_ctx.advance(last_tick, last_index)  # ensure ctx is at last tick
        self.strategy._eod_force_close(last_tick, last_index, bar_ctx)

        # ── 9. Post-period hook ───────────────────────────────────────────────
        self.strategy.on_day_end(bar_ctx)
