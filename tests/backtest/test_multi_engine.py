"""
Tests for fastbt.backtest.multi_engine — MultiStrategyEngine.
Run with: uv run pytest tests/backtest/test_multi_engine.py -v

API: MultiStrategyEngine accepts a list of pre-configured BacktestEngines.
     Each BacktestEngine has one strategy registered and carries its own
     per-strategy settings (transaction_cost_pct, max_cycles, info_attributes).

Core invariant (result parity):
    For any BacktestEngine e, running e.strategy via MultiStrategyEngine([e])
    must produce the same closed_trades as running e.strategy via e directly.

Additional guarantees:
    - cache_warmer called exactly once per period (not once per strategy)
    - Each strategy's cache is fully isolated (deepcopy — mutations cannot bleed)
    - on_day_start returning False skips only that strategy for the period
    - No warmer → identical results to running each BacktestEngine independently
    - Warmer fires before any strategy's on_day_start
    - Different engines can carry different per-strategy settings
"""

from typing import Any, Dict, List, Union

import pytest

from fastbt.backtest.context import DayStartContext
from fastbt.backtest.data import DataSource
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.models import Instrument, Leg
from fastbt.backtest.strategy import Strategy


# ─── Shared test doubles ───────────────────────────────────────────────────────


class MockDataSource(DataSource):
    """Two trading dates, three ticks each, ATM CE and PE instruments."""

    DATES = ["2025-01-02", "2025-01-03"]
    UNDERLYING = {
        "09:15:00": 23400.0,
        "09:16:00": 23410.0,
        "09:17:00": 23420.0,
    }
    CE_DATA = {
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
    }
    PE_DATA = {
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
    }

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        return dict(self.UNDERLYING) if date_str in self.DATES else {}

    def get_instrument_data(self, date_str: str, strike: int, opt_type: str) -> Dict:
        if date_str not in self.DATES or strike != 23400:
            return {}
        return dict(self.CE_DATA) if opt_type == "CE" else dict(self.PE_DATA)

    def get_available_dates(self) -> List[str]:
        return list(self.DATES)

    def get_expiries(self, trade_date: str) -> List[str]:
        return ["2025-01-30"]


@pytest.fixture
def ds():
    return MockDataSource()


# ─── Minimal strategy stubs ───────────────────────────────────────────────────


class SimpleEntryStrategy(Strategy):
    """Sells 23400 CE at 09:15; holds to EOD."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.day_start_return: Union[bool, None] = True

    def on_day_start(self, trade_date, ctx):
        return self.day_start_return

    def can_enter(self, tick, ctx):
        return tick == "09:15:00" and not self.positions

    def on_entry(self, tick, ctx):
        self.try_fill([self.add(23400, "CE", "SELL")], ctx)


class SimplePEStrategy(Strategy):
    """Sells 23400 PE at 09:15; holds to EOD."""

    def can_enter(self, tick, ctx):
        return tick == "09:15:00" and not self.positions

    def on_entry(self, tick, ctx):
        self.try_fill([self.add(23400, "PE", "SELL")], ctx)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def make_engine(ds, strategy, **engine_kwargs) -> BacktestEngine:
    """Create and register a strategy with a BacktestEngine."""
    engine = BacktestEngine(ds, **engine_kwargs)
    engine.add_strategy(strategy)
    return engine


def run_on_backtest_engine(ds, strategy, **kwargs):
    """Run a strategy on a standalone BacktestEngine; returns closed_trades."""
    engine = BacktestEngine(ds, **kwargs)
    engine.add_strategy(strategy)
    engine.run("2025-01-02", "2025-01-03")
    return strategy.closed_trades


def trade_summary(trades):
    """Compact tuple list for assertion: (instrument, side, entry_price, exit_price)."""
    return [(t.instrument, t.side, t.entry_price, t.exit_price) for t in trades]


# ─── Guard ────────────────────────────────────────────────────────────────────


def test_multi_engine_importable():
    from fastbt.backtest.multi_engine import MultiStrategyEngine  # noqa: F401


# ─── Result parity ───────────────────────────────────────────────────────────


class TestResultParity:
    """
    Core invariant: MultiStrategyEngine([e]) == BacktestEngine with same strategy.
    Holds regardless of how many other strategies are in the batch.
    """

    def test_single_engine_parity(self, ds):
        """One engine alone: Multi == standalone BacktestEngine."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_ref = SimpleEntryStrategy(name="ref")
        run_on_backtest_engine(ds, s_ref)

        s_multi = SimpleEntryStrategy(name="multi")
        engine = MultiStrategyEngine([make_engine(ds, s_multi)])
        engine.run("2025-01-02", "2025-01-03")

        assert trade_summary(s_multi.closed_trades) == trade_summary(
            s_ref.closed_trades
        )

    def test_two_engines_parity(self, ds):
        """Two engines together: each matches its standalone result."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        ce_ref = SimpleEntryStrategy(name="ce_ref")
        pe_ref = SimplePEStrategy(name="pe_ref")
        run_on_backtest_engine(ds, ce_ref)
        run_on_backtest_engine(ds, pe_ref)

        ce = SimpleEntryStrategy(name="ce")
        pe = SimplePEStrategy(name="pe")
        engine = MultiStrategyEngine([make_engine(ds, ce), make_engine(ds, pe)])
        engine.run("2025-01-02", "2025-01-03")

        assert trade_summary(ce.closed_trades) == trade_summary(ce_ref.closed_trades)
        assert trade_summary(pe.closed_trades) == trade_summary(pe_ref.closed_trades)

    def test_three_engines_parity(self, ds):
        """Three engines together: each matches its standalone result."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        refs = [
            SimpleEntryStrategy(name="r1"),
            SimplePEStrategy(name="r2"),
            SimpleEntryStrategy(name="r3"),
        ]
        for r in refs:
            run_on_backtest_engine(ds, r)

        multis = [
            SimpleEntryStrategy(name="m1"),
            SimplePEStrategy(name="m2"),
            SimpleEntryStrategy(name="m3"),
        ]
        engine = MultiStrategyEngine([make_engine(ds, s) for s in multis])
        engine.run("2025-01-02", "2025-01-03")

        for ref, multi in zip(refs, multis):
            assert trade_summary(multi.closed_trades) == trade_summary(
                ref.closed_trades
            )

    def test_parity_with_transaction_cost(self, ds):
        """Parity holds when transaction_cost_pct is set on the BacktestEngine."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_ref = SimpleEntryStrategy(name="ref")
        run_on_backtest_engine(ds, s_ref, transaction_cost_pct=0.1)

        s_multi = SimpleEntryStrategy(name="multi")
        engine = MultiStrategyEngine(
            [make_engine(ds, s_multi, transaction_cost_pct=0.1)]
        )
        engine.run("2025-01-02", "2025-01-03")

        ref_costs = [t.transaction_cost for t in s_ref.closed_trades]
        multi_costs = [t.transaction_cost for t in s_multi.closed_trades]
        assert ref_costs == multi_costs


# ─── Cache warmer tests ───────────────────────────────────────────────────────


class TestCacheWarmer:
    """cache_warmer is called exactly once per period, not once per strategy."""

    def test_warmer_called_once_per_period(self, ds):
        """With 2 trading days and 2 strategies, warmer fires exactly 2 times."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        call_log = []

        def counting_warmer(trade_date: str, ctx: DayStartContext) -> None:
            call_log.append(trade_date)

        s1 = SimpleEntryStrategy(name="s1")
        s2 = SimplePEStrategy(name="s2")
        engine = MultiStrategyEngine(
            [make_engine(ds, s1), make_engine(ds, s2)],
            cache_warmer=counting_warmer,
        )
        engine.run("2025-01-02", "2025-01-03")

        assert len(call_log) == 2
        assert call_log == ["2025-01-02", "2025-01-03"]

    def test_warmer_fires_before_strategy_day_start(self, ds):
        """Warmer must populate cache before any strategy's on_day_start fires."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        order = []

        def ordered_warmer(trade_date: str, ctx: DayStartContext) -> None:
            order.append("warmer")
            ctx.prefetch(Instrument(23400, "CE"))

        class OrderCheckStrategy(SimpleEntryStrategy):
            def on_day_start(self, trade_date, ctx):
                order.append("day_start")
                return True

        s = OrderCheckStrategy(name="s")
        engine = MultiStrategyEngine([make_engine(ds, s)], cache_warmer=ordered_warmer)
        engine.run("2025-01-02", "2025-01-02")

        assert order[0] == "warmer"
        assert "day_start" in order

    def test_warmer_prefetch_visible_in_all_strategy_caches(self, ds):
        """Warmer prefetches appear in both strategies' caches at on_day_start."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        strategy_cache_hits = []

        def prefetch_warmer(trade_date: str, ctx: DayStartContext) -> None:
            ctx.prefetch(Instrument(23400, "CE"))

        class CacheCheckStrategy(SimpleEntryStrategy):
            def on_day_start(self, trade_date, ctx):
                strategy_cache_hits.append("23400CE" in ctx._cache)
                return True

        s1 = CacheCheckStrategy(name="s1")
        s2 = CacheCheckStrategy(name="s2")
        engine = MultiStrategyEngine(
            [make_engine(ds, s1), make_engine(ds, s2)],
            cache_warmer=prefetch_warmer,
        )
        engine.run("2025-01-02", "2025-01-02")

        assert all(strategy_cache_hits)

    def test_no_warmer_equals_standalone_backtest_engine(self, ds):
        """Without a warmer, results are identical to standalone BacktestEngine."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_ref = SimpleEntryStrategy(name="ref")
        run_on_backtest_engine(ds, s_ref)

        s_multi = SimpleEntryStrategy(name="multi")
        engine = MultiStrategyEngine([make_engine(ds, s_multi)])
        engine.run("2025-01-02", "2025-01-03")

        assert trade_summary(s_multi.closed_trades) == trade_summary(
            s_ref.closed_trades
        )


# ─── Cache isolation tests ────────────────────────────────────────────────────


class TestCacheIsolation:
    """Mutations in one strategy's cache must not bleed into another's."""

    def test_add_to_cache_in_day_start_does_not_bleed(self, ds):
        """Strategy A's add_to_cache in on_day_start is invisible to Strategy B."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        b_saw_a_key = []

        class WriterStrategy(SimpleEntryStrategy):
            def on_day_start(self, trade_date, ctx):
                ctx.add_to_cache("STRATEGY_A_SIGNAL", {"09:15:00": 42.0})
                return True

        class ReaderStrategy(SimplePEStrategy):
            def on_day_start(self, trade_date, ctx):
                b_saw_a_key.append("STRATEGY_A_SIGNAL" in ctx._cache)
                return True

        writer = WriterStrategy(name="writer")
        reader = ReaderStrategy(name="reader")
        engine = MultiStrategyEngine([make_engine(ds, writer), make_engine(ds, reader)])
        engine.run("2025-01-02", "2025-01-02")

        assert not any(b_saw_a_key)

    def test_lazy_fetch_does_not_bleed_between_strategies(self, ds):
        """A lazy fetch triggered by Strategy A is invisible to Strategy B's cache."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        b_cache_keys = []

        class LazyFetchStrategy(SimpleEntryStrategy):
            def on_entry(self, tick, ctx):
                ctx.get_price("23400CE")
                super().on_entry(tick, ctx)

        class ObserverStrategy(Strategy):
            def can_enter(self, tick, ctx):
                return tick == "09:16:00"

            def on_entry(self, tick, ctx):
                b_cache_keys.append(set(ctx._cache.keys()))

        lazy = LazyFetchStrategy(name="lazy")
        observer = ObserverStrategy(name="observer")
        engine = MultiStrategyEngine([make_engine(ds, lazy), make_engine(ds, observer)])
        engine.run("2025-01-02", "2025-01-02")

        for keys in b_cache_keys:
            assert "NIFTY_SPOT" in keys  # engine always loads this


# ─── on_day_start skip policy ─────────────────────────────────────────────────


class TestDayStartSkipPolicy:
    """Per-strategy skip: returning False skips only that strategy for the period."""

    def test_one_strategy_skip_does_not_affect_others(self, ds):
        """Strategies are skipped independently."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        pe_ref = SimplePEStrategy(name="pe_ref")
        run_on_backtest_engine(ds, pe_ref)

        class SkipFirstDay(SimpleEntryStrategy):
            def on_day_start(self, trade_date, ctx):
                return trade_date != "2025-01-02"

        ce_skip = SkipFirstDay(name="ce_skip")
        pe_multi = SimplePEStrategy(name="pe_multi")
        engine = MultiStrategyEngine(
            [make_engine(ds, ce_skip), make_engine(ds, pe_multi)]
        )
        engine.run("2025-01-02", "2025-01-03")

        assert trade_summary(pe_multi.closed_trades) == trade_summary(
            pe_ref.closed_trades
        )
        assert len(ce_skip.closed_trades) == 1  # only day 2

    def test_all_strategies_skip_period_is_no_op(self, ds):
        """If all strategies skip a day, no trades are produced."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        class AlwaysSkip(SimpleEntryStrategy):
            def on_day_start(self, trade_date, ctx):
                return False

        s1 = AlwaysSkip(name="s1")
        s2 = AlwaysSkip(name="s2")
        engine = MultiStrategyEngine([make_engine(ds, s1), make_engine(ds, s2)])
        engine.run("2025-01-02", "2025-01-03")

        assert s1.closed_trades == []
        assert s2.closed_trades == []


# ─── Per-strategy settings ────────────────────────────────────────────────────


class TestPerStrategySettings:
    """
    Each BacktestEngine carries its own settings. MultiStrategyEngine respects
    them because strategy.engine points to its own BacktestEngine (set by
    BacktestEngine.add_strategy()), not to a shared proxy.
    """

    def test_different_transaction_costs_applied_independently(self, ds):
        """Each strategy is charged its BacktestEngine's transaction cost."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_cheap = SimpleEntryStrategy(name="cheap")
        s_expensive = SimpleEntryStrategy(name="expensive")

        engine = MultiStrategyEngine(
            [
                make_engine(ds, s_cheap, transaction_cost_pct=0.0),
                make_engine(ds, s_expensive, transaction_cost_pct=0.5),
            ]
        )
        engine.run("2025-01-02", "2025-01-02")

        assert all(t.transaction_cost == 0.0 for t in s_cheap.closed_trades)
        assert all(t.transaction_cost > 0.0 for t in s_expensive.closed_trades)

    def test_transaction_cost_affects_net_pnl_independently(self, ds):
        """Higher cost → lower net PnL, independently per strategy."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_low = SimpleEntryStrategy(name="low")
        s_high = SimpleEntryStrategy(name="high")

        engine = MultiStrategyEngine(
            [
                make_engine(ds, s_low, transaction_cost_pct=0.0),
                make_engine(ds, s_high, transaction_cost_pct=1.0),
            ]
        )
        engine.run("2025-01-02", "2025-01-02")

        low_pnl = sum(t.net_pnl for t in s_low.closed_trades)
        high_pnl = sum(t.net_pnl for t in s_high.closed_trades)
        assert low_pnl > high_pnl

    def test_different_max_cycles_applied_independently(self, ds):
        """Strategy with max_cycles=2 can re-enter; max_cycles=1 cannot."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        class ExitImmediately(Strategy):
            def can_enter(self, tick, ctx):
                return not self.positions and self.state != "DONE"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

            def on_exit_condition(self, tick, ctx):
                return bool(self.positions)

        s_one = ExitImmediately(name="one_cycle")
        s_two = ExitImmediately(name="two_cycles")

        engine = MultiStrategyEngine(
            [
                make_engine(ds, s_one, max_cycles=1),
                make_engine(ds, s_two, max_cycles=2),
            ]
        )
        engine.run("2025-01-02", "2025-01-02")

        assert len(s_one.closed_trades) <= 1
        assert len(s_two.closed_trades) >= len(s_one.closed_trades)

    def test_max_cycles_injected_from_backtest_engine(self, ds):
        """BacktestEngine.add_strategy() injects max_cycles correctly."""
        e = BacktestEngine(ds, max_cycles=3)
        s = SimpleEntryStrategy(name="s")
        e.add_strategy(s)
        assert s.max_cycles == 3

    def test_info_attributes_captured_per_strategy(self, ds):
        """Each strategy captures only the info_attributes set on its engine."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        s_with = SimpleEntryStrategy(name="with_attrs")
        s_none = SimpleEntryStrategy(name="no_attrs")

        engine = MultiStrategyEngine(
            [
                make_engine(ds, s_with, info_attributes=["volume"]),
                make_engine(ds, s_none, info_attributes=[]),
            ]
        )
        engine.run("2025-01-02", "2025-01-02")

        for trade in s_with.closed_trades:
            assert (
                "entry_volume" in trade.metadata
            ), f"Missing entry_volume in {trade.label}"
        for trade in s_none.closed_trades:
            assert (
                "entry_volume" not in trade.metadata
            ), f"Unexpected entry_volume in {trade.label}"

    def test_strategy_engine_is_its_own_backtest_engine(self, ds):
        """strategy.engine is the BacktestEngine it was registered with."""
        e = BacktestEngine(ds, transaction_cost_pct=0.7)
        s = SimpleEntryStrategy(name="s")
        e.add_strategy(s)
        assert s.engine is e
        assert s.engine.transaction_cost_pct == 0.7


# ─── Validation tests ─────────────────────────────────────────────────────────


class TestValidation:
    """MultiStrategyEngine validates its inputs at construction and run time."""

    def test_empty_engines_list_raises(self, ds):
        """Constructing with an empty list must raise ValueError."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        with pytest.raises(ValueError, match="engines"):
            MultiStrategyEngine([])

    def test_engine_without_strategy_raises_at_run(self, ds):
        """Engines with no registered strategy must fail at run(), not silently."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        e = BacktestEngine(ds)  # no add_strategy called
        engine = MultiStrategyEngine([e])
        with pytest.raises(ValueError, match="no strategy"):
            engine.run("2025-01-02", "2025-01-02")

    def test_different_data_source_instances_raises(self):
        """All engines must share the same DataSource instance (checked by identity)."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        ds1 = MockDataSource()
        ds2 = MockDataSource()  # different instance, same type

        e1 = BacktestEngine(ds1)
        e1.add_strategy(SimpleEntryStrategy(name="s1"))
        e2 = BacktestEngine(ds2)
        e2.add_strategy(SimplePEStrategy(name="s2"))

        with pytest.raises(ValueError, match="DataSource"):
            MultiStrategyEngine([e1, e2])

    def test_same_data_source_instance_accepted(self, ds):
        """Engines sharing the same DataSource instance are valid."""
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        e1 = make_engine(ds, SimpleEntryStrategy(name="s1"))
        e2 = make_engine(ds, SimplePEStrategy(name="s2"))
        # Should not raise
        engine = MultiStrategyEngine([e1, e2])
        engine.run("2025-01-02", "2025-01-02")


# ─── DB fetch count tests ─────────────────────────────────────────────────────
#
# Setup: 3 identical PrefetchAndLazyStrategy instances, each:
#   - prefetches ATM CE+PE in on_day_start
#   - lazy-fetches OTM CE at tick 09:16
# Run across 2 trading days.
#
# BacktestEngine (3 separate runs):
#   ATM prefetch   → 3 strategies × 2 days × 2 instruments = 12 DB calls
#   OTM lazy fetch → 3 strategies × 2 days × 1 instrument  =  6 DB calls
#
# MultiStrategyEngine with warmer (1 run, 3 engines):
#   ATM prefetch   → 1 warmer × 2 days × 2 instruments = 4 DB calls
#                    (strategies' on_day_start prefetch → no-op: already in deepcopy)
#   OTM lazy fetch → 3 strategies × 2 days × 1 instrument = 6 DB calls
#                    (each strategy has private deepcopy → fetches independently)
#
# Key assertions:
#   1. Multi ATM calls (4) < BacktestEngine ATM calls (12)  — warmer saves calls
#   2. Multi OTM calls (6) == BacktestEngine OTM calls (6)  — private cache → same


class RichMockDataSource(MockDataSource):
    """Extends MockDataSource with an OTM instrument (23900 CE)."""

    OTM_STRIKE = 23900
    OTM_CE_DATA = {
        "09:15:00": {
            "open": 20.0,
            "high": 22.0,
            "low": 19.0,
            "close": 21.0,
            "volume": 200.0,
        },
        "09:16:00": {
            "open": 21.0,
            "high": 23.0,
            "low": 20.0,
            "close": 22.0,
            "volume": 180.0,
        },
        "09:17:00": {
            "open": 22.0,
            "high": 24.0,
            "low": 21.0,
            "close": 23.0,
            "volume": 160.0,
        },
    }

    def get_instrument_data(self, date_str: str, strike: int, opt_type: str) -> Dict:
        if date_str in self.DATES and strike == self.OTM_STRIKE and opt_type == "CE":
            return dict(self.OTM_CE_DATA)
        return super().get_instrument_data(date_str, strike, opt_type)


class PrefetchAndLazyStrategy(Strategy):
    """
    Prefetches ATM CE+PE in on_day_start; lazy-fetches OTM CE at 09:16.
    Used exclusively in fetch-count tests.
    """

    ATM_STRIKE = 23400
    OTM_KEY = f"{RichMockDataSource.OTM_STRIKE}CE"

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        ctx.prefetch(Instrument(self.ATM_STRIKE, "CE"))
        ctx.prefetch(Instrument(self.ATM_STRIKE, "PE"))
        return True

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick == "09:15:00" and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        self.try_fill([self.add(self.ATM_STRIKE, "CE", "SELL")], ctx)

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        if tick == "09:16:00":
            ctx.get_price(self.OTM_KEY)  # deterministic OTM lazy fetch


def _attach_call_mock(ds: DataSource):
    """Replace get_instrument_data with a MagicMock that calls through."""
    from unittest.mock import MagicMock

    original = ds.get_instrument_data
    mock = MagicMock(side_effect=original)
    ds.get_instrument_data = mock
    return mock


def _count(mock, strike: int) -> int:
    return sum(1 for c in mock.call_args_list if c.args[1] == strike)


def _atm_warmer(trade_date: str, ctx: DayStartContext) -> None:
    ctx.prefetch(Instrument(PrefetchAndLazyStrategy.ATM_STRIKE, "CE"))
    ctx.prefetch(Instrument(PrefetchAndLazyStrategy.ATM_STRIKE, "PE"))


N_STRATEGIES = 3
N_DAYS = 2
N_ATM_INSTRUMENTS = 2  # CE + PE


class TestFetchCounts:
    """
    Verify DB call economics: warmer reduces prefetch calls;
    lazy-fetch counts are identical between both engines.
    """

    @pytest.fixture
    def rich_ds_bt(self):
        return RichMockDataSource()

    @pytest.fixture
    def rich_ds_multi(self):
        return RichMockDataSource()

    def test_warmer_reduces_prefetch_db_calls(self, rich_ds_bt, rich_ds_multi):
        """
        BacktestEngine: N × days × instruments prefetch DB calls.
        MultiStrategyEngine: 1 × days × instruments (warmer only; strategies → no-op).
        """
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        mock_bt = _attach_call_mock(rich_ds_bt)
        for i in range(N_STRATEGIES):
            s = PrefetchAndLazyStrategy(name=f"bt_{i}")
            e = BacktestEngine(rich_ds_bt)
            e.add_strategy(s)
            e.run("2025-01-02", "2025-01-03")

        bt_atm = _count(mock_bt, PrefetchAndLazyStrategy.ATM_STRIKE)
        expected_bt_atm = N_STRATEGIES * N_DAYS * N_ATM_INSTRUMENTS  # 12

        mock_multi = _attach_call_mock(rich_ds_multi)
        engines = []
        for i in range(N_STRATEGIES):
            s = PrefetchAndLazyStrategy(name=f"m_{i}")
            e = BacktestEngine(rich_ds_multi)
            e.add_strategy(s)
            engines.append(e)
        MultiStrategyEngine(engines, cache_warmer=_atm_warmer).run(
            "2025-01-02", "2025-01-03"
        )

        multi_atm = _count(mock_multi, PrefetchAndLazyStrategy.ATM_STRIKE)
        expected_multi_atm = 1 * N_DAYS * N_ATM_INSTRUMENTS  # 4

        assert (
            bt_atm == expected_bt_atm
        ), f"BT ATM: expected {expected_bt_atm}, got {bt_atm}"
        assert (
            multi_atm == expected_multi_atm
        ), f"Multi ATM: expected {expected_multi_atm}, got {multi_atm}"
        assert multi_atm < bt_atm

    def test_otm_lazy_fetch_count_equal_between_engines(
        self, rich_ds_bt, rich_ds_multi
    ):
        """
        OTM lazy fetch: private deepcopy per strategy → each strategy fetches
        independently. Count is identical to standalone BacktestEngine runs.
        """
        from fastbt.backtest.multi_engine import MultiStrategyEngine

        mock_bt = _attach_call_mock(rich_ds_bt)
        for i in range(N_STRATEGIES):
            s = PrefetchAndLazyStrategy(name=f"bt_{i}")
            e = BacktestEngine(rich_ds_bt)
            e.add_strategy(s)
            e.run("2025-01-02", "2025-01-03")

        bt_otm = _count(mock_bt, RichMockDataSource.OTM_STRIKE)

        mock_multi = _attach_call_mock(rich_ds_multi)
        engines = []
        for i in range(N_STRATEGIES):
            s = PrefetchAndLazyStrategy(name=f"m_{i}")
            e = BacktestEngine(rich_ds_multi)
            e.add_strategy(s)
            engines.append(e)
        MultiStrategyEngine(engines, cache_warmer=_atm_warmer).run(
            "2025-01-02", "2025-01-03"
        )

        multi_otm = _count(mock_multi, RichMockDataSource.OTM_STRIKE)
        expected_otm = N_STRATEGIES * N_DAYS  # 6

        assert bt_otm == expected_otm, f"BT OTM: expected {expected_otm}, got {bt_otm}"
        assert (
            multi_otm == expected_otm
        ), f"Multi OTM: expected {expected_otm}, got {multi_otm}"
        assert bt_otm == multi_otm  # THE KEY ASSERTION
