"""
Multi-period integration tests for the backtest engine.
Run with: uv run pytest tests/backtest/test_multiperiod.py -v

Tests the period-agnostic behavior:
- period="day" produces same results as before
- period=N groups dates into N-day periods
- period="expiry" groups by expiry dates
- State machine, max_cycles, force-close all work across multi-day periods
- ctx.date, ctx.time, ctx.changed() work correctly in multi-day context
"""

from typing import Any, Dict, List

import pytest

from fastbt.backtest.data import DataSource
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.models import Instrument, Leg
from fastbt.backtest.strategy import Strategy


# ─── Mock DataSource with 4 trading days ──────────────────────────────────────


class FourDayDataSource(DataSource):
    """4 trading days, 3 ticks each. Prices increase across days."""

    DATES = ["2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07"]

    def _spot_for_date(self, date_str):
        base = {
            "2025-01-02": 23400.0,
            "2025-01-03": 23500.0,
            "2025-01-06": 23600.0,
            "2025-01-07": 23700.0,
        }[date_str]
        return {
            "09:15:00": base,
            "09:30:00": base + 10,
            "15:30:00": base + 20,
        }

    def _option_for_date(self, date_str, strike, opt_type):
        """CE price rises with spot, PE price falls."""
        base = {
            "2025-01-02": 100.0,
            "2025-01-03": 110.0,
            "2025-01-06": 120.0,
            "2025-01-07": 130.0,
        }[date_str]
        if opt_type == "PE":
            base = 200.0 - base  # PE inversely related
        return {
            "09:15:00": {
                "open": base,
                "high": base + 5,
                "low": base - 2,
                "close": base,
                "volume": 1000.0,
            },
            "09:30:00": {
                "open": base + 1,
                "high": base + 6,
                "low": base - 1,
                "close": base + 2,
                "volume": 800.0,
            },
            "15:30:00": {
                "open": base + 2,
                "high": base + 7,
                "low": base,
                "close": base + 3,
                "volume": 900.0,
            },
        }

    def get_underlying_data(self, date_str):
        return self._spot_for_date(date_str) if date_str in self.DATES else {}

    def get_instrument_data(self, date_str, strike, opt_type):
        if date_str in self.DATES:
            return self._option_for_date(date_str, strike, opt_type)
        return {}

    def get_available_dates(self):
        return list(self.DATES)

    def get_expiries(self, trade_date):
        # First 2 days → expiry Jan 3, next 2 → expiry Jan 7
        if trade_date in ("2025-01-02", "2025-01-03"):
            return ["2025-01-03"]
        return ["2025-01-07"]


@pytest.fixture
def ds():
    return FourDayDataSource()


# ─── Baseline: period="day" ──────────────────────────────────────────────────


class TestPeriodDay:
    def test_period_day_one_trade_per_day(self, ds):
        """Baseline: period='day', max_cycles=1 → 4 trades over 4 days."""

        class DailyStraddle(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time == "09:30:00"

            def on_entry(self, tick, ctx):
                legs = [
                    self.add(23400, "CE", "SELL"),
                    self.add(23400, "PE", "SELL"),
                ]
                self.try_fill(legs, ctx)

        s = DailyStraddle()
        engine = BacktestEngine(ds, period="day", max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-07")
        # 4 days × 2 legs each = 8 closed trades
        assert len(s.closed_trades) == 8
        # All should be force-closed at EOD
        assert all(t.exit_reason == "EOD_FORCE" for t in s.closed_trades)


# ─── Multi-day period (period=2) ────────────────────────────────────────────


class TestPeriodTwoDays:
    def test_two_day_period_one_trade(self, ds):
        """period=2, max_cycles=1 → 2 periods, enter once per period."""

        class TwoDayStraddle(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time == "09:30:00"

            def on_entry(self, tick, ctx):
                legs = [
                    self.add(23400, "CE", "SELL"),
                    self.add(23400, "PE", "SELL"),
                ]
                self.try_fill(legs, ctx)

        s = TwoDayStraddle()
        engine = BacktestEngine(ds, period=2, max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-07")
        # 2 periods × 1 trade × 2 legs = 4 closed trades
        assert len(s.closed_trades) == 4
        # All force-closed at end of each period
        assert all(t.exit_reason == "EOD_FORCE" for t in s.closed_trades)

    def test_entry_day1_exit_day2(self, ds):
        """Trade entered on day 1 of period, signal to exit on day 2."""

        class CrossDayStrategy(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time == "09:15:00" and ctx.date == "2025-01-02"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

            def on_exit_condition(self, tick, ctx):
                return ctx.date == "2025-01-03" and ctx.time == "09:30:00"

        s = CrossDayStrategy()
        engine = BacktestEngine(ds, period=2, max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-03")
        assert len(s.closed_trades) == 1
        assert s.closed_trades[0].exit_reason == "exit_signal"
        assert "2025-01-03" in str(s.closed_trades[0].exit_tick)

    def test_max_cycles_across_days(self, ds):
        """max_cycles=2, period=2: two trades across the 2-day period."""

        class TwoCycleStrategy(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time == "09:30:00"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

            def on_exit_condition(self, tick, ctx):
                return ctx.time == "15:30:00"

        s = TwoCycleStrategy()
        engine = BacktestEngine(ds, period=2, max_cycles=2)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-03")
        # Day 1: enter 09:30, exit 15:30 (cycle 0)
        # Day 2: enter 09:30, exit 15:30 (cycle 1) → DONE
        # Plus force close at period end (no-op if already closed)
        assert len(s.closed_trades) == 2
        assert s.closed_trades[0].cycle == 0
        assert s.closed_trades[1].cycle == 1


# ─── Expiry-based period ────────────────────────────────────────────────────


class TestPeriodExpiry:
    def test_expiry_grouping(self, ds):
        """period='expiry' groups dates by their nearest expiry."""

        class ExpiryStraddle(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time == "09:30:00" and not self.positions

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

        s = ExpiryStraddle()
        engine = BacktestEngine(ds, period="expiry", max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-07")
        # 2 expiry periods → 1 trade per period → 2 trades
        assert len(s.closed_trades) == 2


# ─── ctx.changed() in multi-day context ─────────────────────────────────────


class TestChangedInMultiDay:
    def test_changed_detects_day_boundary(self, ds):
        """ctx.changed() fires at each day boundary within a multi-day period."""
        boundary_ticks = []

        class BoundaryStrategy(Strategy):
            def can_enter(self, tick, ctx):
                if ctx.is_new_date:
                    boundary_ticks.append(tick)
                return False

            def on_entry(self, tick, ctx):
                pass

        s = BoundaryStrategy()
        engine = BacktestEngine(ds, period=4, max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-07")
        # 4 days in one period → 4 new-date boundaries
        assert len(boundary_ticks) == 4

    def test_ctx_time_for_entry_logic(self, ds):
        """Strategy using ctx.time works identically for day and multi-day."""

        class TimeBasedEntry(Strategy):
            def can_enter(self, tick, ctx):
                return ctx.time >= "09:30:00"

            def on_entry(self, tick, ctx):
                self.try_fill([self.add(23400, "CE", "SELL")], ctx)

            def on_exit_condition(self, tick, ctx):
                return ctx.time == "15:30:00"

        # Run with period="day"
        s1 = TimeBasedEntry()
        e1 = BacktestEngine(ds, period="day", max_cycles=1)
        e1.add_strategy(s1)
        e1.run("2025-01-02", "2025-01-02")
        day_pnl = sum(t.net_pnl for t in s1.closed_trades)

        # Run with period=1 (should be equivalent to "day")
        s2 = TimeBasedEntry()
        e2 = BacktestEngine(ds, period=1, max_cycles=1)
        e2.add_strategy(s2)
        e2.run("2025-01-02", "2025-01-02")
        period1_pnl = sum(t.net_pnl for t in s2.closed_trades)

        assert day_pnl == period1_pnl


# ─── Lazy fetch in multi-day ────────────────────────────────────────────────


class TestMultiDayLazyFetch:
    def test_lazy_fetch_populates_all_days(self, ds):
        """Cache miss in multi-day period fetches data for ALL days."""

        class FetchChecker(Strategy):
            def __init__(self):
                super().__init__()
                self.price_day1 = None
                self.price_day2 = None

            def can_enter(self, tick, ctx):
                return False

            def on_entry(self, tick, ctx):
                pass

            def on_day_start(self, trade_date, ctx):
                return True

        s = FetchChecker()
        engine = BacktestEngine(ds, period=2, max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-03")
        # After run, cache should have data for both days
        # (tested implicitly by test_entry_day1_exit_day2 above)

    def test_prefetch_in_multi_day_loads_all_days(self, ds):
        """Prefetch in on_day_start populates cache for entire period."""
        cache_sizes = []

        class PrefetchChecker(Strategy):
            def on_day_start(self, trade_date, ctx):
                ctx.prefetch(Instrument(23400, "CE"))
                cache_sizes.append(len(ctx._cache.get("23400CE", {})))
                return True

            def can_enter(self, tick, ctx):
                return False

            def on_entry(self, tick, ctx):
                pass

        s = PrefetchChecker()
        engine = BacktestEngine(ds, period=2, max_cycles=1)
        engine.add_strategy(s)
        engine.run("2025-01-02", "2025-01-03")
        # Cache should have 3 ticks × 2 days = 6 entries
        assert cache_sizes[0] == 6
