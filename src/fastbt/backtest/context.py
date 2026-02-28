"""
fastbt.backtest.context
=======================
Context objects passed to Strategy hooks each bar/day.

- DayStartContext : restricted view available during on_day_start()
                   (spot + ATM + prefetch only — no option price lookup)
- BarContext       : full market view within the clock loop
                   (all price getters, lazy fetch with lag, prefetch)

Design decisions:
- BarContext is created ONCE per day and mutated via advance() each tick.
  This avoids the overhead of allocating a new object for every bar.
- The raw cache dict is never exposed to user code. Only tick-bound
  accessors (get_spot, get_price, get_bar) are public — this is what
  prevents look-ahead bias: future data is in memory but unreachable.
- Lag fill-forward: when a tick has no data (illiquid bar), we walk
  backward through the clock to find the last known price. lag=0 means
  live price; lag>0 means N ticks stale; lag=-1 means no data at all.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from fastbt.backtest.data import DataSource
from fastbt.backtest.models import Instrument

logger = logging.getLogger(__name__)


def _parse_instrument_key(key: str) -> Instrument:
    """
    Parse a cache-key string back into an Instrument.

    Phase 1 shortcut: assumes key format '{strike}{opt_type}' with
    opt_type being 'CE' or 'PE' (exactly 2 characters).
    Example: '23600CE' → Instrument(23600, 'CE')

    Phase 2: replace with a proper SymbolParser for multi-expiry support.
    """
    opt_type = key[-2:]  # "CE" or "PE"
    strike = int(key[:-2])
    return Instrument(strike=strike, opt_type=opt_type)


def _compute_atm(spot: float, step: int) -> int:
    """Round spot to nearest strike step. Uses Python's built-in round()."""
    return int(round(spot / step) * step)


class DayStartContext:
    """
    Restricted context available only during Strategy.on_day_start().

    Provides:
      - get_spot()    : underlying price at first bar of day
      - get_atm()     : ATM strike derived from spot
      - prefetch()    : optional performance hint to warm the cache
      - trade_date    : the current trading date string

    Does NOT provide: get_price(), get_bar(), try_fill().
    Option data may not be in cache yet when on_day_start fires.
    """

    def __init__(self, trade_date: str, cache: Dict, data_source: DataSource):
        self.trade_date = trade_date
        self._cache = cache
        self._data_source = data_source

    def get_spot(self) -> Tuple[Optional[float], int]:
        """
        Return underlying price at the first available tick of the day.

        Returns:
            (price, lag) where lag=0 means exact match, -1 means no data.
        """
        spot_data = self._cache.get("NIFTY_SPOT")
        if not spot_data:
            return None, -1
        first_tick = next(iter(spot_data))
        return float(spot_data[first_tick]), 0

    def get_atm(self, step: int = 50) -> int:
        """
        Return ATM strike rounded to the nearest step.

        Falls back to 0 if no spot data is available.
        """
        price, _ = self.get_spot()
        if price is None:
            return 0
        return _compute_atm(price, step)

    def prefetch(self, instrument: Instrument) -> None:
        """
        Optional performance hint — warm the cache for a known instrument.

        The cache fetches lazily anyway if skipped. This is a no-op if
        the instrument is already in cache.
        """
        key = instrument.key()
        if key in self._cache:
            return  # already warm, no-op
        data = self._data_source.get_instrument_data(
            self.trade_date, instrument.strike, instrument.opt_type
        )
        if data:
            self._cache[key] = data


class BarContext:
    """
    Full market context available within the clock loop (run_one_cycle and
    all Strategy sub-methods: on_entry, on_adjust, on_exit, on_exit_condition).

    Created once per day and mutated via advance() each tick to avoid
    per-bar object allocation.

    Look-ahead bias guarantee:
        All price getters use self.tick as the lookup key. Future ticks
        are present in the cache but never read by these methods.
    """

    def __init__(
        self,
        cache: Dict,
        data_source: DataSource,
        trade_date: str,
        clock: List[Any],
    ):
        self._cache = cache
        self._data_source = data_source
        self._trade_date = trade_date
        self._clock = clock

        # Mutated by advance() each loop iteration
        self.tick: Any = None
        self.tick_index: int = -1

    def advance(self, tick: Any, tick_index: int) -> None:
        """Called by BacktestEngine once per clock iteration."""
        self.tick = tick
        self.tick_index = tick_index

    # ─── Public price accessors ───────────────────────────────────────────

    def get_spot(self) -> Tuple[Optional[float], int]:
        """
        Return underlying price at current tick.

        Returns:
            (price, lag) — lag=0 live, lag>0 fill-forward ticks, -1 no data.
        """
        spot_data = self._cache.get("NIFTY_SPOT")
        if not spot_data:
            return None, -1

        if self.tick in spot_data:
            return float(spot_data[self.tick]), 0

        # Fill-forward: walk backward through clock
        for lag in range(1, self.tick_index + 1):
            prev_tick = self._clock[self.tick_index - lag]
            if prev_tick in spot_data:
                return float(spot_data[prev_tick]), lag

        return None, -1

    def get_price(self, instrument_key: str) -> Tuple[Optional[float], int]:
        """
        Return close price of an instrument at current tick.

        Triggers a lazy DuckDB fetch if the instrument is not yet in cache.
        Returns (None, -1) if instrument has no data at all.

        Returns:
            (close_price, lag) — lag=0 live, lag>0 fill-forward, -1 no data.
        """
        bar, lag = self._get_bar_with_lag(instrument_key)
        if bar is None:
            return None, lag
        return bar.get("close"), lag

    def get_bar(
        self, instrument_key: str
    ) -> Tuple[Optional[Dict[str, float]], int]:
        """
        Return full OHLCV dict for an instrument at current tick.

        Same lag semantics as get_price().

        Returns:
            (bar_dict, lag) or (None, -1) if no data.
        """
        return self._get_bar_with_lag(instrument_key)

    def get_atm(self, step: int = 50) -> int:
        """ATM strike derived from current tick's spot price."""
        price, _ = self.get_spot()
        if price is None:
            return 0
        return _compute_atm(price, step)

    def prefetch(self, instrument: Instrument) -> None:
        """
        Optional performance hint — warm the cache for a known instrument.

        The cache fetches lazily anyway if skipped. No-op on cache hit.
        """
        key = instrument.key()
        if key in self._cache:
            return
        self._lazy_fetch(key)

    # ─── Internal helpers ─────────────────────────────────────────────────

    def _get_bar_with_lag(
        self, instrument_key: str
    ) -> Tuple[Optional[Dict[str, float]], int]:
        """
        Core lookup: return (bar, lag) for instrument_key at current tick.

        If instrument not in cache, triggers a lazy fetch first.
        If tick has no bar, walks backward (fill-forward) until one is found.
        """
        if instrument_key not in self._cache:
            self._lazy_fetch(instrument_key)

        inst_data = self._cache.get(instrument_key)
        if not inst_data:
            return None, -1

        # Exact match
        if self.tick in inst_data:
            return inst_data[self.tick], 0

        # Fill-forward: walk backward through clock positions
        for lag in range(1, self.tick_index + 1):
            prev_tick = self._clock[self.tick_index - lag]
            if prev_tick in inst_data:
                return inst_data[prev_tick], lag

        return None, -1

    def _lazy_fetch(self, instrument_key: str) -> None:
        """
        Fetch full-day data for instrument_key from the DataSource into cache.

        Phase 1: parses instrument_key string to get (strike, opt_type).
        Logs a warning to guide users toward prefetch() for performance.

        If the instrument key cannot be parsed or returns no data, the cache
        entry is left absent so subsequent lookups return (None, -1).
        """
        try:
            instrument = _parse_instrument_key(instrument_key)
        except (ValueError, IndexError):
            logger.warning(
                "Cannot parse instrument key '%s'. "
                "Expected format: '{strike}{CE|PE}', e.g. '23600CE'.",
                instrument_key,
            )
            return

        logger.warning(
            "Lazy fetch for '%s' at tick '%s'. "
            "Consider calling ctx.prefetch(Instrument(%d, '%s')) in "
            "on_day_start() for better performance.",
            instrument_key,
            self.tick,
            instrument.strike,
            instrument.opt_type,
        )

        data = self._data_source.get_instrument_data(
            self._trade_date, instrument.strike, instrument.opt_type
        )
        if data:
            self._cache[instrument_key] = data
