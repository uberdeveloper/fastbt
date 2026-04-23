"""
fastbt.backtest.multi_engine
============================
MultiStrategyEngine — orchestrates a list of pre-configured BacktestEngines
in lockstep with a shared warm cache, while keeping each strategy's cache
fully isolated via per-strategy deep copy.

Design principle
-----------------
The single-strategy contract ("one engine per strategy") is preserved:

    e1 = BacktestEngine(ds, transaction_cost_pct=0.1)
    e1.add_strategy(my_strategy)

    e2 = BacktestEngine(ds, max_cycles=2)
    e2.add_strategy(other_strategy)

    MultiStrategyEngine([e1, e2], cache_warmer=warm_fn).run(start, end)

MultiStrategyEngine adds nothing to individual engine/strategy configuration.
It only orchestrates the shared warm-up phase and lockstep clock loop.

Per-period lifecycle
---------------------
1.  _warm_cache cleared; NIFTY_SPOT loaded.
2.  cache_warmer(trade_date, DayStartContext(_warm_cache)) called ONCE.
    All prefetches land in _warm_cache (shared staging area).
3.  Per engine/strategy:
    a.  strategy._reset_for_new_day()   ← state machine reset (IDLE, cycle=0)
    b.  s_cache = copy.deepcopy(_warm_cache)  ← fully independent per-strategy cache
    c.  strategy.on_day_start(date, DayStartContext(s_cache))
        → returns False: strategy skipped for this period
    d.  BarContext(s_cache, ...) created — private to this strategy
4.  Clock loop: every tick → run_one_cycle for every active strategy.
5.  EOD force close + on_day_end per active strategy.

Cache isolation guarantee
--------------------------
copy.deepcopy() copies every level of nesting, so per-bar OHLCV dicts are
independent objects per strategy. Mutating a bar value in strategy A's cache
cannot affect strategy B's cache at any nesting depth.

Parallelisation note (future)
------------------------------
For concurrent parameter sweeps use process-per-engine:
    Pass (filepath, warmer_fn, strategy_cls, params, start, end) to workers.
    Each worker reconstructs its own DataSource + BacktestEngine.
    cache_warmer must be a module-level function (picklable); avoid lambdas.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from fastbt.backtest.context import BarContext, DayStartContext
from fastbt.backtest.data import DataSource
from fastbt.backtest.engine import (
    BacktestEngine,
    group_by_day,
    group_by_expiry,
    group_by_n_days,
)
from fastbt.backtest.strategy import Strategy

logger = logging.getLogger(__name__)

# cache_warmer signature:
#   trade_date: first date of the period (str)
#   ctx:        DayStartContext backed by the shared _warm_cache
# Populate via ctx.prefetch() / ctx.add_to_cache(). Must return None.
CacheWarmerFn = Callable[[str, DayStartContext], None]


class MultiStrategyEngine:
    """
    Orchestrates a list of pre-configured BacktestEngines in lockstep with
    a shared warm cache.

    Each BacktestEngine retains its own settings (transaction_cost_pct,
    max_cycles, info_attributes) and its own fully-isolated deep-copied cache.
    Results are identical to running each BacktestEngine independently.

    All registered engines must share the same DataSource instance —
    cache sharing only makes sense when data comes from the same source.
    """

    def __init__(
        self,
        engines: List[BacktestEngine],
        cache_warmer: Optional[CacheWarmerFn] = None,
        clock: Optional[List[Any]] = None,
        period: Union[str, int] = "day",
    ) -> None:
        """
        Args:
            engines:      Non-empty list of BacktestEngines, each with a strategy
                          registered via engine.add_strategy(). All engines must
                          share the same DataSource instance (checked by identity).
            cache_warmer: Optional callable (trade_date, DayStartContext) → None.
                          Called once per period against the shared _warm_cache
                          before any strategy's on_day_start. Use ctx.prefetch()
                          to pre-load instruments common across strategies.
                          If None: pure lazy-fetch behaviour, identical to running
                          each BacktestEngine independently.
            clock:        Optional list of tick values. Auto-derived from NIFTY_SPOT
                          keys if None. Governs all strategies in lockstep —
                          per-engine clocks are not used.
            period:       Grouping mode: "day" (default), "expiry", or int.

        Raises:
            ValueError: If engines is empty.
            ValueError: If any engine has a different DataSource instance.
        """
        if not engines:
            raise ValueError(
                "engines must not be empty. "
                "Pass at least one BacktestEngine with a registered strategy."
            )

        first_ds = engines[0].data_source
        for idx, engine in enumerate(engines[1:], start=1):
            if engine.data_source is not first_ds:
                raise ValueError(
                    f"All engines must share the same DataSource instance. "
                    f"Engine at index {idx} has a different DataSource."
                )

        self.engines: List[BacktestEngine] = engines
        self.data_source: DataSource = first_ds
        self.cache_warmer: Optional[CacheWarmerFn] = cache_warmer
        self.user_clock: Optional[List[Any]] = clock
        self.period: Union[str, int] = period

        # Shared staging area for the cache warmer.
        # Populated once per period; deep-copied independently per strategy.
        self._warm_cache: Dict = {}

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self, start_date: str, end_date: str) -> None:
        """
        Run all registered engines/strategies for every period in [start_date, end_date].

        Args:
            start_date: First day to include, e.g. "2025-01-02".
            end_date:   Last day to include, e.g. "2025-03-31".

        Raises:
            ValueError: If any engine has no strategy registered.
            ValueError: If period is invalid.
        """
        for idx, engine in enumerate(self.engines):
            if engine.strategy is None:
                raise ValueError(
                    f"Engine at index {idx} has no strategy registered. "
                    f"Call engine.add_strategy(strategy) before run()."
                )

        all_dates = self.data_source.get_available_dates()
        trading_days = [d for d in all_dates if start_date <= d <= end_date]

        if self.period == "day":
            periods = group_by_day(trading_days)
        elif self.period == "expiry":
            periods = group_by_expiry(trading_days, self.data_source)
        elif isinstance(self.period, int):
            periods = group_by_n_days(trading_days, self.period)
        else:
            raise ValueError(
                f"Invalid period: {self.period!r}. Use 'day', 'expiry', or an integer."
            )

        logger.info(
            "MultiStrategyEngine: %d engines, %d periods (%d days) [%s → %s]",
            len(self.engines),
            len(periods),
            len(trading_days),
            start_date,
            end_date,
        )

        for period_dates in periods:
            self._run_period(period_dates)

    # ── Internal lifecycle ────────────────────────────────────────────────────

    def _run_period(self, period_dates: List[str]) -> None:
        """
        Execute the full per-period lifecycle for all engines/strategies.

        Steps (fixed, non-negotiable order):
          1. Clear _warm_cache; load NIFTY_SPOT.
          2. cache_warmer — once, against shared _warm_cache.
          3. Per engine: state reset + deep-copy cache + on_day_start.
          4. Clock loop: run_one_cycle for every active strategy per tick.
          5. EOD force close + on_day_end per active strategy.
        """
        multi_day = len(period_dates) > 1

        # ── 1. Clear warm cache; load NIFTY_SPOT ──────────────────────────────
        self._warm_cache.clear()

        merged_underlying: Dict[str, float] = {}
        for d in period_dates:
            daily = self.data_source.get_underlying_data(d)
            for time_key, price in daily.items():
                key = f"{d} {time_key}" if multi_day else time_key
                merged_underlying[key] = price
        self._warm_cache["NIFTY_SPOT"] = merged_underlying

        # ── 2. Derive clock ───────────────────────────────────────────────────
        clock: List[Any] = (
            self.user_clock
            if self.user_clock is not None
            else list(self._warm_cache["NIFTY_SPOT"].keys())
        )

        if not clock:
            logger.warning(
                "No clock ticks for period %s (underlying data empty). Skipping.",
                period_dates,
            )
            return

        # ── 3. Cache warmer — once, against shared _warm_cache ────────────────
        if self.cache_warmer is not None:
            warm_ctx = DayStartContext(
                period_dates[0],
                self._warm_cache,
                self.data_source,
                period_dates=period_dates,
            )
            self.cache_warmer(period_dates[0], warm_ctx)

        # ── 4. Per-engine: state reset + deep copy + on_day_start ─────────────
        active: List[Tuple[Strategy, BarContext]] = []

        for engine in self.engines:
            strategy = engine.strategy

            # Reset strategy state machine for this period.
            # Note: this is unrelated to cache — it resets IDLE/ACTIVE/DONE,
            # cycle counter, and open positions. closed_trades is preserved.
            strategy._reset_for_new_day()
            strategy.trade_date = period_dates[0]

            # Full deep copy: every nesting level is an independent object.
            # Warmer's prefetched data is present in _warm_cache and thus in
            # every strategy's copy — without any additional DB calls.
            # Mutations (lazy fetches, add_to_cache) only affect this copy.
            s_cache: Dict = dict(self._warm_cache)

            s_day_ctx = DayStartContext(
                period_dates[0],
                s_cache,
                engine.data_source,
                period_dates=period_dates,
            )
            should_run = strategy.on_day_start(period_dates[0], s_day_ctx)
            if should_run is False:
                logger.info(
                    "Strategy '%s' skipped period %s (on_day_start returned False).",
                    strategy.name,
                    period_dates,
                )
                continue

            bar_ctx = BarContext(
                s_cache,
                engine.data_source,
                period_dates[0],
                clock,
                period_dates=period_dates,
            )
            active.append((strategy, bar_ctx))

        if not active:
            logger.info(
                "All strategies skipped period %s. No clock loop executed.",
                period_dates,
            )
            return

        # ── 5. Clock loop ─────────────────────────────────────────────────────
        for tick_index, tick in enumerate(clock):
            for strategy, bar_ctx in active:
                bar_ctx.advance(tick, tick_index)
                strategy.run_one_cycle(tick, bar_ctx)

        # ── 6. EOD force close — always fires at period end ───────────────────
        last_tick = clock[-1]
        last_index = len(clock) - 1
        for strategy, bar_ctx in active:
            bar_ctx.advance(last_tick, last_index)
            strategy._eod_force_close(last_tick, last_index, bar_ctx)

        # ── 7. Post-period hook ───────────────────────────────────────────────
        for strategy, bar_ctx in active:
            strategy.on_day_end(bar_ctx)
