"""
Tests for fastbt.backtest.context — DayStartContext and BarContext.
Run with: uv run pytest tests/backtest/test_context.py -v
"""
from typing import Dict, List
from unittest.mock import MagicMock

import pytest

from fastbt.backtest.context import BarContext, DayStartContext
from fastbt.backtest.data import DataSource
from fastbt.backtest.models import Instrument


# ─── Mock DataSource ──────────────────────────────────────────────────────────


class MockDataSource(DataSource):
    """Minimal stub — returns deterministic data without touching disk."""

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        return {
            "09:15:00": 23400.0,
            "09:16:00": 23410.0,
            "09:17:00": 23420.0,
            "09:18:00": 23430.0,
        }

    def get_instrument_data(
        self, date_str: str, strike: int, opt_type: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Returns 4 bars for 23400CE/PE with 09:16 deliberately missing to
        test fill-forward lag behaviour.
        """
        if strike == 23400 and opt_type in ("CE", "PE"):
            return {
                "09:15:00": {"open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000.0},
                # 09:16:00 intentionally missing — simulates illiquid bar
                "09:17:00": {"open": 103.0, "high": 108.0, "low": 101.0, "close": 106.0, "volume": 800.0},
                "09:18:00": {"open": 104.0, "high": 110.0, "low": 102.0, "close": 107.0, "volume": 900.0},
            }
        return {}

    def get_available_dates(self) -> List[str]:
        return ["2025-01-02"]

    def get_expiries(self, trade_date: str) -> List[str]:
        return ["2025-01-30"]


@pytest.fixture
def ds():
    return MockDataSource()


@pytest.fixture
def clock():
    return ["09:15:00", "09:16:00", "09:17:00", "09:18:00"]


@pytest.fixture
def populated_cache():
    """Cache with underlying already loaded (as engine does before on_day_start)."""
    return {
        "NIFTY_SPOT": {
            "09:15:00": 23400.0,
            "09:16:00": 23410.0,
            "09:17:00": 23420.0,
            "09:18:00": 23430.0,
        }
    }


# ─── DayStartContext ──────────────────────────────────────────────────────────


class TestDayStartContext:
    def test_get_spot_returns_first_bar(self, populated_cache, ds):
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        price, lag = ctx.get_spot()
        assert price == 23400.0
        assert lag == 0

    def test_get_spot_empty_cache_returns_none(self, ds):
        ctx = DayStartContext("2025-01-02", {}, ds)
        price, lag = ctx.get_spot()
        assert price is None
        assert lag == -1

    def test_get_atm_from_spot(self, populated_cache, ds):
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        atm = ctx.get_atm(step=50)
        assert atm == 23400  # 23400 rounds to 23400

    def test_get_atm_step_100(self, populated_cache, ds):
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        atm = ctx.get_atm(step=100)
        assert atm == 23400

    def test_prefetch_loads_into_cache(self, populated_cache, ds):
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        inst = Instrument(23400, "CE")
        ctx.prefetch(inst)
        assert inst.key() in populated_cache
        assert "09:15:00" in populated_cache[inst.key()]

    def test_prefetch_is_noop_on_cache_hit(self, populated_cache, ds):
        """Second prefetch must NOT call data_source again."""
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        inst = Instrument(23400, "CE")
        # Pre-warm cache manually
        populated_cache[inst.key()] = {"09:15:00": {"close": 999.0}}
        spy = MagicMock(wraps=ds.get_instrument_data)
        ds.get_instrument_data = spy  # type: ignore

        ctx.prefetch(inst)
        spy.assert_not_called()

    def test_trade_date_accessible(self, populated_cache, ds):
        ctx = DayStartContext("2025-01-02", populated_cache, ds)
        assert ctx.trade_date == "2025-01-02"


# ─── BarContext — advance() and tick tracking ─────────────────────────────────


class TestBarContextAdvance:
    def test_tick_and_index_update(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        assert ctx.tick == "09:15:00"
        assert ctx.tick_index == 0

    def test_advance_updates_each_iteration(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        for i, tick in enumerate(clock):
            ctx.advance(tick, i)
        assert ctx.tick == "09:18:00"
        assert ctx.tick_index == 3


# ─── BarContext — get_spot() ──────────────────────────────────────────────────


class TestBarContextGetSpot:
    def test_exact_tick_live(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        price, lag = ctx.get_spot()
        assert price == 23400.0
        assert lag == 0

    def test_spot_at_different_tick(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:17:00", 2)
        price, lag = ctx.get_spot()
        assert price == 23420.0
        assert lag == 0

    def test_missing_spot_tick_fill_forward(self, ds, clock):
        """Spot is missing at 09:16 — should fill forward from 09:15."""
        cache = {
            "NIFTY_SPOT": {
                "09:15:00": 23400.0,
                # 09:16 missing
                "09:17:00": 23420.0,
            }
        }
        ctx = BarContext(cache, ds, "2025-01-02", clock)
        ctx.advance("09:16:00", 1)
        price, lag = ctx.get_spot()
        assert price == 23400.0  # fill-forward from 09:15
        assert lag == 1

    def test_no_spot_data_returns_none(self, ds, clock):
        ctx = BarContext({}, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        price, lag = ctx.get_spot()
        assert price is None
        assert lag == -1


# ─── BarContext — get_price() with lazy fetch and lag ─────────────────────────


class TestBarContextGetPrice:
    def test_exact_tick_live(self, populated_cache, ds, clock):
        """Price at exact tick → lag=0."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        # Trigger lazy fetch for 23400CE
        price, lag = ctx.get_price("23400CE")
        assert price == 102.0
        assert lag == 0

    def test_fill_forward_on_missing_tick(self, populated_cache, ds, clock):
        """09:16 is missing for 23400CE — returns 09:15 price with lag=1."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        # First access at 09:15 (loads full-day cache)
        ctx.advance("09:15:00", 0)
        ctx.get_price("23400CE")
        # Now move to 09:16 (missing bar)
        ctx.advance("09:16:00", 1)
        price, lag = ctx.get_price("23400CE")
        assert price == 102.0  # 09:15 close, fill-forward
        assert lag == 1

    def test_data_available_after_gap(self, populated_cache, ds, clock):
        """09:17 has data after 09:16 gap — lag=0 again."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        ctx.get_price("23400CE")
        ctx.advance("09:16:00", 1)
        ctx.get_price("23400CE")
        ctx.advance("09:17:00", 2)
        price, lag = ctx.get_price("23400CE")
        assert price == 106.0  # 09:17 close
        assert lag == 0

    def test_instrument_not_in_cache_triggers_lazy_fetch(self, populated_cache, ds, clock):
        """Cache miss → lazy fetch → instrument added to cache."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        assert "23400CE" not in populated_cache
        price, lag = ctx.get_price("23400CE")
        assert "23400CE" in populated_cache  # now populated
        assert price is not None

    def test_lazy_fetch_only_called_once(self, populated_cache, ds, clock):
        """Second get_price call uses cache, does NOT trigger another DB fetch."""
        spy = MagicMock(wraps=ds.get_instrument_data)
        ds_spy = MockDataSource()
        ds_spy.get_instrument_data = spy  # type: ignore

        ctx = BarContext(populated_cache, ds_spy, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        ctx.get_price("23400CE")
        ctx.get_price("23400CE")        # second call
        ctx.advance("09:16:00", 1)
        ctx.get_price("23400CE")        # third call, different tick

        spy.assert_called_once()  # DB hit exactly once

    def test_unknown_instrument_returns_none(self, populated_cache, ds, clock):
        """Instrument not in data source → (None, -1)."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        price, lag = ctx.get_price("99999CE")
        assert price is None
        assert lag == -1


# ─── BarContext — get_bar() ───────────────────────────────────────────────────


class TestBarContextGetBar:
    def test_returns_ohlcv_dict(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        bar, lag = ctx.get_bar("23400CE")
        assert lag == 0
        assert isinstance(bar, dict)
        assert {"open", "high", "low", "close", "volume"}.issubset(bar.keys())

    def test_bar_fill_forward_on_missing_tick(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        ctx.get_bar("23400CE")
        ctx.advance("09:16:00", 1)
        bar, lag = ctx.get_bar("23400CE")
        assert lag == 1
        assert bar["close"] == 102.0  # 09:15 bar, fill-forward

    def test_none_on_missing_instrument(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        bar, lag = ctx.get_bar("99999CE")
        assert bar is None
        assert lag == -1


# ─── BarContext — get_atm() ───────────────────────────────────────────────────


class TestBarContextGetAtm:
    def test_atm_from_current_spot(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:15:00", 0)
        atm = ctx.get_atm(step=50)
        assert atm == 23400

    def test_atm_updates_with_spot(self, populated_cache, ds, clock):
        """ATM at 09:18 uses the higher spot (23430)."""
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        ctx.advance("09:18:00", 3)
        atm = ctx.get_atm(step=50)
        assert atm == 23450


# ─── BarContext — prefetch() ──────────────────────────────────────────────────


class TestBarContextPrefetch:
    def test_prefetch_loads_into_cache(self, populated_cache, ds, clock):
        ctx = BarContext(populated_cache, ds, "2025-01-02", clock)
        inst = Instrument(23400, "CE")
        ctx.prefetch(inst)
        assert "23400CE" in populated_cache

    def test_prefetch_noop_on_hit(self, populated_cache, ds, clock):
        spy = MagicMock(wraps=ds.get_instrument_data)
        ds_spy = MockDataSource()
        ds_spy.get_instrument_data = spy  # type: ignore

        populated_cache["23400CE"] = {"09:15:00": {"close": 999.0}}
        ctx = BarContext(populated_cache, ds_spy, "2025-01-02", clock)
        ctx.prefetch(Instrument(23400, "CE"))
        spy.assert_not_called()
