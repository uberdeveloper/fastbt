"""
Tests for deepcopy-based cache isolation in MultiStrategyEngine.

These tests verify that per-strategy cache copies produced by copy.deepcopy()
are fully independent from each other and from the original _warm_cache at
every level of nesting.  They operate on plain dicts — no engine lifecycle
needed — making them fast, deterministic, and focused solely on the isolation
property.

Run with: uv run pytest tests/backtest/test_cache_isolation.py -v
"""

import copy
from typing import Dict

import pytest


# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_warm_cache() -> Dict:
    """
    Build a minimal _warm_cache structure that mirrors what MultiStrategyEngine
    produces after loading NIFTY_SPOT and prefetching two instruments.

    Structure mirrors the real cache layout:
      cache["INSTRUMENT_KEY"]["HH:MM:SS"]["ohlcv_field"] = float
    """
    return {
        "NIFTY_SPOT": {
            "09:15:00": 23400.0,
            "09:16:00": 23410.0,
            "09:17:00": 23420.0,
        },
        "23400CE": {
            "09:15:00": {
                "open": 100.0,
                "high": 105.0,
                "low": 98.0,
                "close": 102.0,
                "volume": 1000.0,
            },
            "09:16:00": {
                "open": 103.0,
                "high": 108.0,
                "low": 101.0,
                "close": 106.0,
                "volume": 800.0,
            },
            "09:17:00": {
                "open": 104.0,
                "high": 110.0,
                "low": 102.0,
                "close": 107.0,
                "volume": 900.0,
            },
        },
        "23400PE": {
            "09:15:00": {
                "open": 90.0,
                "high": 95.0,
                "low": 88.0,
                "close": 92.0,
                "volume": 900.0,
            },
            "09:16:00": {
                "open": 91.0,
                "high": 96.0,
                "low": 89.0,
                "close": 93.0,
                "volume": 850.0,
            },
            "09:17:00": {
                "open": 92.0,
                "high": 97.0,
                "low": 90.0,
                "close": 94.0,
                "volume": 800.0,
            },
        },
    }


@pytest.fixture
def warm_cache() -> Dict:
    return make_warm_cache()


# ─── Identity tests (id() at every nesting level) ────────────────────────────


class TestDeepCopyObjectIdentity:
    """
    Verify that deepcopy produces distinct objects at every nesting level.
    If any level shares an id(), a mutation in one strategy's cache will
    bleed into another.
    """

    def test_outer_cache_dict_is_different_object(self, warm_cache):
        """Top-level cache dicts are distinct objects."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)
        assert id(cache_a) != id(cache_b)

    def test_bar_by_tick_dict_is_different_object(self, warm_cache):
        """Level-2: bar-by-tick dicts are distinct — not shared references."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        assert id(cache_a["23400CE"]) != id(cache_b["23400CE"])

    def test_bar_by_tick_dict_differs_from_warm_cache(self, warm_cache):
        """Level-2 dicts are also distinct from the original warm_cache."""
        cache_a = copy.deepcopy(warm_cache)

        assert id(cache_a["23400CE"]) != id(warm_cache["23400CE"])

    def test_per_bar_ohlcv_dict_is_different_object(self, warm_cache):
        """Level-3: per-bar OHLCV dicts are the innermost shared risk — must be distinct."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        assert id(cache_a["23400CE"]["09:15:00"]) != id(cache_b["23400CE"]["09:15:00"])

    def test_per_bar_ohlcv_dict_differs_from_warm_cache(self, warm_cache):
        """Level-3 dicts are also distinct from the original warm_cache."""
        cache_a = copy.deepcopy(warm_cache)

        assert id(cache_a["23400CE"]["09:15:00"]) != id(
            warm_cache["23400CE"]["09:15:00"]
        )

    def test_nifty_spot_dict_is_different_object(self, warm_cache):
        """NIFTY_SPOT (flat dict of floats) is also a distinct object per copy."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        assert id(cache_a["NIFTY_SPOT"]) != id(cache_b["NIFTY_SPOT"])
        assert id(cache_a["NIFTY_SPOT"]) != id(warm_cache["NIFTY_SPOT"])


# ─── Value equality tests ─────────────────────────────────────────────────────


class TestDeepCopyValueEquality:
    """Verify that all values are faithfully preserved after deepcopy."""

    def test_nifty_spot_values_preserved(self, warm_cache):
        cache_a = copy.deepcopy(warm_cache)
        for tick, price in warm_cache["NIFTY_SPOT"].items():
            assert cache_a["NIFTY_SPOT"][tick] == price

    def test_ohlcv_values_preserved_for_all_fields(self, warm_cache):
        cache_a = copy.deepcopy(warm_cache)
        for instrument in ("23400CE", "23400PE"):
            for tick, bar in warm_cache[instrument].items():
                for field, value in bar.items():
                    assert (
                        cache_a[instrument][tick][field] == value
                    ), f"Mismatch at [{instrument}][{tick}][{field}]"

    def test_multiple_copies_have_identical_values(self, warm_cache):
        """N independent copies all carry the same original values."""
        copies = [copy.deepcopy(warm_cache) for _ in range(5)]
        for c in copies:
            assert (
                c["23400CE"]["09:15:00"]["close"]
                == warm_cache["23400CE"]["09:15:00"]["close"]
            )


# ─── Mutation isolation tests ─────────────────────────────────────────────────


class TestDeepCopyMutationIsolation:
    """
    Verify that in-place mutations (the real isolation risk) do not bleed
    between copies or back to the original warm_cache.
    """

    def test_bar_value_mutation_does_not_bleed_between_copies(self, warm_cache):
        """Mutating an OHLCV value in cache_a does not affect cache_b."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        original_close = cache_b["23400CE"]["09:15:00"]["close"]
        cache_a["23400CE"]["09:15:00"]["close"] = 999_999.0

        assert cache_b["23400CE"]["09:15:00"]["close"] == original_close

    def test_bar_value_mutation_does_not_affect_warm_cache(self, warm_cache):
        """Mutating a copy's bar value does not corrupt the master warm_cache."""
        original_close = warm_cache["23400CE"]["09:15:00"]["close"]
        cache = copy.deepcopy(warm_cache)
        cache["23400CE"]["09:15:00"]["close"] = 0.0

        assert warm_cache["23400CE"]["09:15:00"]["close"] == original_close

    def test_n_mutations_do_not_corrupt_warm_cache(self, warm_cache):
        """Creating N copies and mutating all does not touch warm_cache."""
        original_close = warm_cache["23400CE"]["09:15:00"]["close"]
        caches = [copy.deepcopy(warm_cache) for _ in range(5)]
        for c in caches:
            c["23400CE"]["09:15:00"]["close"] = 0.0

        assert warm_cache["23400CE"]["09:15:00"]["close"] == original_close

    def test_adding_new_key_to_copy_does_not_bleed(self, warm_cache):
        """Adding a new top-level key to cache_a is invisible to cache_b."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        cache_a["STRATEGY_A_SIGNAL"] = {"09:15:00": 42.0}

        assert "STRATEGY_A_SIGNAL" not in cache_b
        assert "STRATEGY_A_SIGNAL" not in warm_cache

    def test_adding_nested_key_to_copy_does_not_bleed(self, warm_cache):
        """Adding a new tick to a bar-by-tick dict in cache_a is invisible to cache_b."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        cache_a["23400CE"]["09:20:00"] = {"open": 99.0, "close": 100.0}

        assert "09:20:00" not in cache_b["23400CE"]
        assert "09:20:00" not in warm_cache["23400CE"]

    def test_nifty_spot_mutation_does_not_bleed(self, warm_cache):
        """NIFTY_SPOT price mutation in one copy is isolated."""
        cache_a = copy.deepcopy(warm_cache)
        cache_b = copy.deepcopy(warm_cache)

        cache_a["NIFTY_SPOT"]["09:15:00"] = 99999.0

        assert cache_b["NIFTY_SPOT"]["09:15:00"] == warm_cache["NIFTY_SPOT"]["09:15:00"]


# ─── End-to-end: MultiStrategyEngine produces isolated caches ─────────────────


class TestMultiEngineProducesIsolatedCaches:
    """
    Verify the isolation property via the actual MultiStrategyEngine lifecycle
    rather than raw dict operations.  Uses the internal _warm_cache to confirm
    that deepcopy is applied correctly during _run_period.
    """

    def test_strategy_caches_are_distinct_objects(self):
        """
        Two strategies running in MultiStrategyEngine must have caches that
        are distinct at the top, bar-by-tick, and per-bar levels.
        """
        from unittest.mock import MagicMock

        from fastbt.backtest.context import DayStartContext
        from fastbt.backtest.data import DataSource
        from fastbt.backtest.engine import BacktestEngine
        from fastbt.backtest.models import Instrument
        from fastbt.backtest.multi_engine import MultiStrategyEngine
        from fastbt.backtest.strategy import Strategy

        class RecordingDataSource(DataSource):
            """Minimal DataSource that records strategy cache objects."""

            DATES = ["2025-01-02"]
            UNDERLYING = {"09:15:00": 23400.0}
            CE_DATA = {
                "09:15:00": {
                    "open": 100.0,
                    "high": 105.0,
                    "low": 98.0,
                    "close": 102.0,
                    "volume": 1000.0,
                }
            }

            def get_underlying_data(self, date_str):
                return dict(self.UNDERLYING) if date_str in self.DATES else {}

            def get_instrument_data(self, date_str, strike, opt_type):
                return dict(self.CE_DATA) if date_str in self.DATES else {}

            def get_available_dates(self):
                return list(self.DATES)

            def get_expiries(self, trade_date):
                return ["2025-01-30"]

        captured_caches = []

        class CacheRecorder(Strategy):
            def on_day_start(self, trade_date, ctx):
                captured_caches.append(ctx._cache)
                ctx.prefetch(Instrument(23400, "CE"))
                return True

            def can_enter(self, tick, ctx):
                return False

            def on_entry(self, tick, ctx):
                pass

        ds = RecordingDataSource()
        s1 = CacheRecorder(name="s1")
        s2 = CacheRecorder(name="s2")

        e1 = BacktestEngine(ds)
        e1.add_strategy(s1)
        e2 = BacktestEngine(ds)
        e2.add_strategy(s2)

        def warmer(trade_date, ctx):
            ctx.prefetch(Instrument(23400, "CE"))

        engine = MultiStrategyEngine([e1, e2], cache_warmer=warmer)
        engine.run("2025-01-02", "2025-01-02")

        assert len(captured_caches) == 2, "Both strategies must fire on_day_start"

        cache_s1, cache_s2 = captured_caches
        # Top-level dicts are different objects
        assert id(cache_s1) != id(cache_s2)
        # Bar-by-tick dicts for the prefetched instrument are different objects
        assert "23400CE" in cache_s1 and "23400CE" in cache_s2
        assert id(cache_s1["23400CE"]) != id(cache_s2["23400CE"])
        # Per-bar OHLCV dicts are different objects
        assert id(cache_s1["23400CE"]["09:15:00"]) != id(
            cache_s2["23400CE"]["09:15:00"]
        )
        # But values are identical
        assert (
            cache_s1["23400CE"]["09:15:00"]["close"]
            == cache_s2["23400CE"]["09:15:00"]["close"]
        )
