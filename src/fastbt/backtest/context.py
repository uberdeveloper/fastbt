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
from typing import Any, Dict, List, Optional, Tuple

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


def _fetch_and_merge(
    data_source: DataSource,
    period_dates: List[str],
    strike: int,
    opt_type: str,
) -> Dict:
    """Fetch instrument data for all dates in period, merge into one dict.

    Single-day periods use simple keys ('09:15:00').
    Multi-day periods use composite keys ('2025-01-02 09:15:00').
    """
    multi_day = len(period_dates) > 1
    merged: Dict = {}
    for d in period_dates:
        daily_data = data_source.get_instrument_data(d, strike, opt_type)
        for time_key, bar in daily_data.items():
            key = f"{d} {time_key}" if multi_day else time_key
            merged[key] = bar
    return merged


class DayStartContext:
    """
    Restricted context available only during Strategy.on_day_start().

    Provides:
      - get_spot()       : underlying price at first bar of day
      - get_atm()        : ATM strike derived from spot
      - prefetch()       : optional performance hint to warm the cache
      - add_to_cache()   : load custom external data (VIX, macro, etc.)
      - trade_date       : the current trading date string

    Does NOT provide: get_price(), get_bar(), try_fill().
    Option data may not be in cache yet when on_day_start fires.
    """

    def __init__(
        self,
        trade_date: str,
        cache: Dict,
        data_source: DataSource,
        period_dates: Optional[List[str]] = None,
    ):
        self.trade_date = trade_date
        self._cache = cache
        self._data_source = data_source
        self._period_dates = period_dates or [trade_date]

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
        data = _fetch_and_merge(
            self._data_source,
            self._period_dates,
            instrument.strike,
            instrument.opt_type,
        )
        if data:
            self._cache[key] = data

    def add_to_cache(self, key: str, data: Dict[Any, Any]) -> None:
        """
        Load custom external data into the shared cache under a user-chosen key.

        The data dict must be keyed by the same tick values as the clock so
        that BarContext.get_price() can do tick-aligned lookups with lag.

        Example (VIX loaded in on_day_start):
            vix_data = my_loader.get_vix(trade_date)  # {"09:15:00": 18.5, ...}
            ctx.add_to_cache("VIX", vix_data)

            # Then in on_adjust:
            vix, lag = ctx.get_price("VIX")  # same API as options

        Note: clock alignment is the user's responsibility. If the custom data
        uses different tick keys than the clock, fill-forward semantics apply.
        """
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
        period_dates: Optional[List[str]] = None,
    ):
        self._cache = cache
        self._data_source = data_source
        self._trade_date = trade_date
        self._clock = clock
        self._period_dates = period_dates or [trade_date]

        # Mutated by advance() each loop iteration
        self.tick: Any = None
        self.tick_index: int = -1
        self.date: str = trade_date
        self.time: str = ""
        self._prev_tick: Any = None  # for changed() boundary detection

    def advance(self, tick: Any, tick_index: int) -> None:
        """Called by BacktestEngine once per clock iteration."""
        self._prev_tick = self.tick  # store before overwriting
        self.tick = tick
        self.tick_index = tick_index
        # Parse date and time from tick
        tick_str = str(tick)
        if " " in tick_str:
            # Composite tick: "2025-01-02 09:15:00"
            self.date, self.time = tick_str.split(" ", 1)
        else:
            # Simple tick: "09:15:00" — date from trade_date
            self.date = self._trade_date
            self.time = tick_str

    # ─── Read-only helper properties ────────────────────────────────────────────

    @property
    def trade_date(self) -> str:
        """Current trading date string (e.g. '2025-01-02')."""
        return self._trade_date

    @property
    def total_ticks(self) -> int:
        """Total number of ticks in today's clock."""
        return len(self._clock)

    @property
    def is_last_tick(self) -> bool:
        """True if the current tick is the last one before EOD force-close."""
        return self.tick_index == len(self._clock) - 1

    @property
    def ticks_remaining(self) -> int:
        """Number of ticks left after the current one (0 on the last tick)."""
        return max(0, len(self._clock) - self.tick_index - 1)

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
        Return the close price of an instrument (or scalar value for custom data)
        at the current tick.

        Works for two cache formats:
          - Options OHLCV  : cache[key][tick] is a dict — returns bar['close']
          - Custom flat    : cache[key][tick] is a scalar — returns float(value)

        Triggers a lazy DuckDB fetch on cache miss for option keys (CE/PE).
        For custom keys loaded via add_to_cache(), no fetch is attempted.

        Returns:
            (price, lag) — lag=0 live, lag>0 fill-forward, -1 no data.
        """
        bar, lag = self._get_bar_with_lag(instrument_key)
        if bar is None:
            return None, lag
        if isinstance(bar, dict):
            return bar.get("close"), lag  # options OHLCV nested format
        try:
            return float(bar), lag  # custom flat scalar (VIX, macro, etc.)
        except (TypeError, ValueError):
            return None, lag

    def get_bar(self, instrument_key: str) -> Tuple[Optional[Dict[str, float]], int]:
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

    def add_to_cache(self, key: str, data: Dict[Any, Any]) -> None:
        """
        Load custom external data into the shared cache under a user-chosen key.

        Same contract as DayStartContext.add_to_cache().
        Can be called from any strategy hook (on_adjust, on_entry, etc.).
        """
        self._cache[key] = data

    def changed(self, key_fn) -> bool:
        """
        True if key_fn(current_tick) differs from key_fn(previous_tick).

        First tick of period always returns True (no previous tick to compare).

        Usage:
            ctx.changed(lambda t: t.split(' ')[0])   # date boundary
            ctx.changed(lambda t: t[:2])              # hour boundary
        """
        if self._prev_tick is None:
            return True
        return key_fn(str(self.tick)) != key_fn(str(self._prev_tick))

    @property
    def is_new_date(self) -> bool:
        """True when the date component of the tick changed from previous tick."""
        if self._prev_tick is None:
            return True
        prev_str = str(self._prev_tick)
        curr_str = str(self.tick)
        # Extract date: composite "YYYY-MM-DD HH:MM:SS" or simple "HH:MM:SS"
        prev_date = prev_str.split(" ")[0] if " " in prev_str else self._trade_date
        curr_date = curr_str.split(" ")[0] if " " in curr_str else self._trade_date
        return curr_date != prev_date

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

        Only called for option keys (CE/PE). Custom keys loaded via
        add_to_cache() are always in cache already, so this path is never
        hit for them.

        Parse failures are SILENT — the key is not an option symbol and the
        user is responsible for loading it via add_to_cache(). No warning
        is emitted to avoid noise for intentional custom cache keys.

        Successful parse but empty DuckDB result — warns once (data may be
        missing from the parquet for this date/strike combination).
        """
        try:
            instrument = _parse_instrument_key(instrument_key)
        except (ValueError, IndexError):
            # Not an option key — silently skip. User should call add_to_cache()
            # for custom data (VIX, macro, Greeks from external source, etc.).
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

        data = _fetch_and_merge(
            self._data_source,
            self._period_dates,
            instrument.strike,
            instrument.opt_type,
        )
        if data:
            self._cache[instrument_key] = data
