"""
Tests for fastbt.backtest.engine — BacktestEngine orchestrator.
Run with: uv run pytest tests/backtest/test_engine.py -v

Focus on accuracy:
- Per-day flow (cache clear, underlying load, clock loop, EOD close, day end)
- Strategy hooks called in correct order and at correct times
- max_cycles injected correctly
- Auto-clock vs user-defined clock
- Skip-day when on_day_start returns False
- transaction_cost_pct passed through to strategy
- Multi-day accumulation in closed_trades
"""
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock, call, patch

import pytest

from fastbt.backtest.data import DataSource
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.models import Instrument, Leg, Trade
from fastbt.backtest.strategy import Strategy


# ─── Test doubles ─────────────────────────────────────────────────────────────


class MockDataSource(DataSource):
    """Returns two trading dates with minimal tick data."""

    DATES = ["2025-01-02", "2025-01-03"]
    UNDERLYING = {
        "09:15:00": 23400.0,
        "09:16:00": 23410.0,
        "09:17:00": 23420.0,
    }
    CE_DATA = {
        "09:15:00": {"open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000.0},
        "09:16:00": {"open": 103.0, "high": 108.0, "low": 101.0, "close": 106.0, "volume": 800.0},
        "09:17:00": {"open": 104.0, "high": 110.0, "low": 102.0, "close": 107.0, "volume": 900.0},
    }

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        if date_str in self.DATES:
            return dict(self.UNDERLYING)
        return {}

    def get_instrument_data(
        self, date_str: str, strike: int, opt_type: str
    ) -> Dict[str, Dict[str, float]]:
        if date_str in self.DATES and strike == 23400:
            return dict(self.CE_DATA)
        return {}

    def get_available_dates(self) -> List[str]:
        return list(self.DATES)

    def get_expiries(self, trade_date: str) -> List[str]:
        return ["2025-01-30"]


class EventRecordingStrategy(Strategy):
    """Records every hook call and arguments for assertion in tests."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.events: List[str] = []     # ordered event log
        self.day_start_return = True
        self.can_enter_return = False
        self.exit_condition = False
        self.legs_to_fill: Union[List[Leg], Dict[str, Leg], None] = None

    def on_day_start(self, trade_date, ctx):
        self.events.append(f"day_start:{trade_date}")
        return self.day_start_return

    def can_enter(self, tick, ctx):
        return self.can_enter_return

    def on_entry(self, tick, ctx):
        self.events.append(f"entry:{tick}")
        if self.legs_to_fill is not None:
            self.try_fill(self.legs_to_fill, ctx)

    def on_adjust(self, tick, ctx):
        self.events.append(f"adjust:{tick}")

    def on_exit_condition(self, tick, ctx):
        return self.exit_condition

    def on_exit(self, tick, ctx):
        self.events.append(f"exit:{tick}")
        self.close_all(tick, ctx.tick_index, ctx, "exit_signal")

    def on_day_end(self, ctx):
        self.events.append("day_end")


@pytest.fixture
def ds():
    return MockDataSource()


@pytest.fixture
def strategy():
    return EventRecordingStrategy(name="Test")


def make_engine(ds, strategy=None, **kwargs):
    engine = BacktestEngine(ds, **kwargs)
    if strategy:
        engine.add_strategy(strategy)
    return engine


# ─── BacktestEngine initialisation ───────────────────────────────────────────


class TestEngineInit:
    def test_default_transaction_cost(self, ds):
        engine = BacktestEngine(ds)
        assert engine.transaction_cost_pct == 0.0

    def test_custom_transaction_cost(self, ds):
        engine = BacktestEngine(ds, transaction_cost_pct=0.1)
        assert engine.transaction_cost_pct == 0.1

    def test_default_max_cycles(self, ds):
        engine = BacktestEngine(ds)
        assert engine.max_cycles == 1

    def test_custom_max_cycles(self, ds):
        engine = BacktestEngine(ds, max_cycles=3)
        assert engine.max_cycles == 3

    def test_no_strategy_initially(self, ds):
        engine = BacktestEngine(ds)
        assert engine.strategy is None


# ─── add_strategy() ──────────────────────────────────────────────────────────


class TestAddStrategy:
    def test_engine_injected_into_strategy(self, ds, strategy):
        engine = make_engine(ds, strategy)
        assert strategy.engine is engine

    def test_max_cycles_injected_into_strategy(self, ds, strategy):
        engine = BacktestEngine(ds, max_cycles=3)
        engine.add_strategy(strategy)
        assert strategy.max_cycles == 3

    def test_strategy_stored(self, ds, strategy):
        engine = make_engine(ds, strategy)
        assert engine.strategy is strategy


# ─── Per-day flow ─────────────────────────────────────────────────────────────


class TestPerDayFlow:
    def test_on_day_start_called_per_day(self, ds, strategy):
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-03")
        day_starts = [e for e in strategy.events if e.startswith("day_start")]
        assert len(day_starts) == 2

    def test_on_day_start_called_with_correct_dates(self, ds, strategy):
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-03")
        assert "day_start:2025-01-02" in strategy.events
        assert "day_start:2025-01-03" in strategy.events

    def test_day_end_called_per_day(self, ds, strategy):
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-03")
        day_ends = [e for e in strategy.events if e == "day_end"]
        assert len(day_ends) == 2

    def test_skip_day_when_on_day_start_returns_false(self, ds, strategy):
        strategy.day_start_return = False
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-02")
        # No tick events — clock loop was skipped
        tick_events = [e for e in strategy.events if "adjust" in e or "entry" in e]
        assert tick_events == []

    def test_underlying_in_cache_when_on_day_start_fires(self, ds):
        """Engine must load NIFTY_SPOT before on_day_start."""
        cache_at_day_start = {}

        class CacheCheckStrategy(EventRecordingStrategy):
            def on_day_start(self, trade_date, ctx):
                # Record whether underlying was already loaded
                cache_at_day_start[trade_date] = "NIFTY_SPOT" in ctx._cache
                return True

        s = CacheCheckStrategy()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-02")
        assert cache_at_day_start["2025-01-02"] is True

    def test_state_reset_each_day(self, ds, strategy):
        """Strategy state must reset to IDLE at start of each day."""
        reset_states: List[str] = []

        class StateCheckStrategy(EventRecordingStrategy):
            def on_day_start(self, trade_date, ctx):
                reset_states.append(self.state)
                return True

        s = StateCheckStrategy()
        # Manually corrupt state to DONE before run
        s.state = "DONE"
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-03")
        # Both days should have seen IDLE at day start
        assert all(st == "IDLE" for st in reset_states)


# ─── Clock behaviour ──────────────────────────────────────────────────────────


class TestClockBehaviour:
    def test_auto_clock_from_underlying(self, ds, strategy):
        """Auto-clock uses NIFTY_SPOT keys → 3 ticks per day in IDLE scan."""
        all_ticks = []

        class TickTracker(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                all_ticks.append(tick)
                return False  # stay IDLE to see every tick

        s = TickTracker()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-02")
        # Underlying has 3 distinct ticks → can_enter called 3 times
        assert len(all_ticks) == 3
        assert all_ticks[0] == "09:15:00"
        assert all_ticks[-1] == "09:17:00"

    def test_user_clock_overrides_auto(self, ds, strategy):
        """User-provided clock controls iteration regardless of underlying."""
        all_ticks = []

        class TickTracker(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                all_ticks.append(tick)
                return False

        s = TickTracker()
        user_clock = ["09:15:00", "09:16:00"]  # 2 ticks only
        engine = BacktestEngine(ds, clock=user_clock)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-02")
        assert len(all_ticks) == 2
        assert all_ticks == ["09:15:00", "09:16:00"]

    def test_tick_index_increments(self, ds):
        """ctx.tick_index must be 0, 1, 2, … within each day."""
        tick_indices = []

        class IndexTracker(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                tick_indices.append(ctx.tick_index)
                return False

        s = IndexTracker()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-02")
        assert tick_indices == [0, 1, 2]

    def test_tick_index_resets_each_day(self, ds):
        """tick_index must restart at 0 for each new trading day."""
        first_tick_indices = []

        class FirstIndexTracker(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                if ctx.tick_index == 0:
                    first_tick_indices.append(tick)
                return False

        s = FirstIndexTracker()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-03")
        # Both days start at index 0 → both captured
        assert len(first_tick_indices) == 2
        assert all(t == "09:15:00" for t in first_tick_indices)


# ─── EOD force close ─────────────────────────────────────────────────────────


class TestEodForceClose:
    def test_open_positions_closed_at_eod(self, ds):
        """Positions not closed by strategy must be force-closed by engine."""

        class HoldStrategy(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                return tick == "09:15:00"

            def on_entry(self, tick, ctx):
                self.try_fill(
                    [self.add(23400, "CE", "SELL")],
                    ctx,
                )
            # No exit condition — relies on EOD

        s = HoldStrategy()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-02")
        assert len(s.closed_trades) == 1
        assert s.closed_trades[0].exit_reason == "EOD_FORCE"
        assert s.positions == {}

    def test_day_end_called_after_eod_close(self, ds, strategy):
        """on_day_end must fire AFTER EOD force close."""
        order = []

        class OrderCheckStrategy(EventRecordingStrategy):
            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

            def on_day_end(self, ctx):
                order.append(("day_end", len(self.closed_trades)))

        s = OrderCheckStrategy()
        s.can_enter_return = True
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-02")
        # closed_trades should already have the EOD-closed trade by day_end
        assert order[0][1] >= 1

    def test_state_is_done_after_run(self, ds, strategy):
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-02")
        assert strategy.state == "DONE"


# ─── Multi-day accumulation ───────────────────────────────────────────────────


class TestMultiDayAccumulation:
    def test_closed_trades_accumulate_across_days(self, ds):
        """One trade per day × 2 days = 2 closed trades total."""

        class DailyEntryStrategy(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                return tick == "09:15:00" and not self.positions

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

        s = DailyEntryStrategy()
        engine = make_engine(ds, s)
        engine.run("2025-01-02", "2025-01-03")
        assert len(s.closed_trades) == 2

    def test_date_range_filter(self, ds, strategy):
        """engine.run should only process days within start_date..end_date."""
        engine = make_engine(ds, strategy)
        engine.run("2025-01-02", "2025-01-02")   # only one day
        day_starts = [e for e in strategy.events if e.startswith("day_start")]
        assert len(day_starts) == 1
        assert "day_start:2025-01-02" in strategy.events
        assert "day_start:2025-01-03" not in strategy.events


# ─── transaction_cost_pct propagation ────────────────────────────────────────


class TestTransactionCostPropagation:
    def test_cost_applied_to_closed_trades(self, ds):
        class CostStrategy(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                return tick == "09:15:00"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

        s = CostStrategy()
        engine = BacktestEngine(ds, transaction_cost_pct=0.1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-02")
        trade = s.closed_trades[0]
        assert trade.transaction_cost > 0.0

    def test_zero_cost_by_default(self, ds):
        class CostStrategy(EventRecordingStrategy):
            def can_enter(self, tick, ctx):
                return tick == "09:15:00"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

        s = CostStrategy()
        engine = make_engine(ds, s)  # default cost=0.0
        engine.run("2025-01-02", "2025-01-02")
        trade = s.closed_trades[0]
        assert trade.transaction_cost == 0.0


# ─── No strategy guard ────────────────────────────────────────────────────────


class TestNoStrategy:
    def test_run_without_strategy_raises(self, ds):
        engine = BacktestEngine(ds)
        with pytest.raises(ValueError, match="No strategy"):
            engine.run("2025-01-02", "2025-01-02")
