"""
fastbt.backtest.engine
======================
BacktestEngine — orchestrates the clock loop, context management,
and per-day strategy lifecycle.

Per-day sequence (enforced, non-negotiable):
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
from typing import Any, Dict, List, Optional

from fastbt.backtest.context import BarContext, DayStartContext
from fastbt.backtest.data import DataSource
from fastbt.backtest.strategy import Strategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Orchestrates a single-strategy backtest over a date range.

    Responsibilities:
    - Iterate over trading days provided by the DataSource
    - Manage a shared cache (clear + reload each day)
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
    ):
        """
        Args:
            data_source:          DataSource implementation (DuckDBParquetLoader).
            transaction_cost_pct: Round-trip cost as % of notional, passed to Trade.close().
            max_cycles:           How many entry-exit cycles the strategy may do per day.
            clock:                Optional list of tick values. If None, auto-derived
                                  from NIFTY_SPOT keys (underlying timestamps).
        """
        self.data_source = data_source
        self.transaction_cost_pct = transaction_cost_pct
        self.max_cycles = max_cycles
        self.user_clock = clock        # None = auto-derive each day from underlying
        self.strategy: Optional[Strategy] = None
        self._cache: Dict = {}         # shared cache, cleared each day

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

        logger.info(
            "BacktestEngine: running %d days [%s → %s]",
            len(trading_days),
            start_date,
            end_date,
        )

        for trade_date in trading_days:
            self._run_day(trade_date)

    def _run_day(self, trade_date: str) -> None:
        """
        Execute the full per-day lifecycle for one trading date.

        All steps are mandatory and execute in a fixed, documented order.
        """
        # ── 1. Clear cache ────────────────────────────────────────────────────
        self._cache.clear()

        # ── 2. Load underlying price data — always, before anything else ──────
        self._cache["NIFTY_SPOT"] = self.data_source.get_underlying_data(trade_date)

        # ── 3. Derive or use clock ────────────────────────────────────────────
        clock = self.user_clock if self.user_clock is not None \
            else list(self._cache["NIFTY_SPOT"].keys())

        if not clock:
            logger.warning(
                "No clock ticks for %s (underlying data empty). Skipping day.",
                trade_date,
            )
            return

        # ── 4. Reset strategy per-day state ───────────────────────────────────
        self.strategy._reset_for_new_day()

        # ── 5. Create contexts ─────────────────────────────────────────────────
        day_ctx = DayStartContext(trade_date, self._cache, self.data_source)
        bar_ctx = BarContext(self._cache, self.data_source, trade_date, clock)

        # ── 6. on_day_start — user can prefetch and bail ──────────────────────
        should_run = self.strategy.on_day_start(trade_date, day_ctx)
        if should_run is False:
            logger.info("Strategy skipped day %s (on_day_start returned False).", trade_date)
            return

        # ── 7. Clock loop ─────────────────────────────────────────────────────
        for tick_index, tick in enumerate(clock):
            bar_ctx.advance(tick, tick_index)
            self.strategy.run_one_cycle(tick, bar_ctx)

        # ── 8. EOD force close — always fires, regardless of strategy state ───
        last_tick = clock[-1]
        last_index = len(clock) - 1
        bar_ctx.advance(last_tick, last_index)   # ensure ctx is at last tick
        self.strategy._eod_force_close(last_tick, last_index, bar_ctx)

        # ── 9. Post-day hook ──────────────────────────────────────────────────
        self.strategy.on_day_end(bar_ctx)
