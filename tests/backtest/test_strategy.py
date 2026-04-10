"""
Tests for fastbt.backtest.strategy — Strategy base class.
Run with: uv run pytest tests/backtest/test_strategy.py -v

Focus: state machine accuracy, try_fill all-or-nothing, positions dict,
cycle management, EOD force close. These directly affect engine correctness.
"""

from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock

import pytest

from fastbt.backtest.models import Instrument, Leg, Trade
from fastbt.backtest.strategy import Strategy


# ─── Test doubles ─────────────────────────────────────────────────────────────


class MockBarContext:
    """Minimal ctx stub — returns predefined prices and bars."""

    def __init__(
        self,
        tick: Any = "09:15:00",
        tick_index: int = 0,
        prices: Optional[Dict[str, tuple]] = None,
        atm: int = 23600,
        bars: Optional[Dict[str, tuple]] = None,
    ):
        self.tick = tick
        self.tick_index = tick_index
        # prices: {instrument_key: (price, lag)}  lag=0 → live
        self._prices: Dict[str, tuple] = prices or {}
        self._atm = atm
        # bars: {instrument_key: (bar_dict, lag)}
        self._bars: Dict[str, tuple] = bars or {}

    def get_price(self, key: str):
        return self._prices.get(key, (None, -1))

    def get_atm(self, step: int = 50) -> int:
        return self._atm

    def get_bar(self, key: str):
        """Returns (bar_dict, lag) or (None, -1) if no bar data."""
        return self._bars.get(key, (None, -1))


class MockEngine:
    """Minimal engine stub for testing info_attributes capture."""

    def __init__(self, info_attributes=None, transaction_cost_pct=0.0):
        self.info_attributes: List[str] = info_attributes or []
        self.transaction_cost_pct: float = transaction_cost_pct


class ConcreteStrategy(Strategy):
    """Minimal concrete Strategy for testing. Tracks call counts."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.day_start_calls = 0
        self.entry_calls = 0
        self.adjust_calls = 0
        self.exit_calls = 0

        # Test control switches
        self.day_start_return = True  # False → skip day
        self.can_enter_return = False  # toggle to trigger entries
        self.exit_condition = False  # toggle to trigger exits
        self.legs_to_fill: Union[List[Leg], Dict[str, Leg], None] = None

    def on_day_start(self, trade_date, ctx):
        self.day_start_calls += 1
        return self.day_start_return

    def can_enter(self, tick, ctx):
        return self.can_enter_return

    def on_entry(self, tick, ctx):
        self.entry_calls += 1
        if self.legs_to_fill is not None:
            self.try_fill(self.legs_to_fill, ctx)

    def on_adjust(self, tick, ctx):
        self.adjust_calls += 1

    def on_exit_condition(self, tick, ctx):
        return self.exit_condition

    def on_exit(self, tick, ctx):
        self.exit_calls += 1
        self.close_all(tick, ctx.tick_index, ctx, reason="exit_signal")


@pytest.fixture
def strategy():
    return ConcreteStrategy(name="TestStrategy")


def live_ctx(*instrument_keys, tick="09:15:00", idx=0, price=100.0):
    """Create a MockBarContext where all given keys have a live price (lag=0)."""
    prices = {k: (price, 0) for k in instrument_keys}
    return MockBarContext(tick=tick, tick_index=idx, prices=prices)


def stale_ctx(*instrument_keys, tick="09:15:00", idx=0, price=100.0):
    """Create a MockBarContext where all given keys have a stale price (lag=1)."""
    prices = {k: (price, 1) for k in instrument_keys}
    return MockBarContext(tick=tick, tick_index=idx, prices=prices)


def empty_ctx(tick="09:15:00", idx=0):
    """Create a MockBarContext with no price data."""
    return MockBarContext(tick=tick, tick_index=idx, prices={})


# ─── Strategy.add() ───────────────────────────────────────────────────────────


class TestStrategySAdd:
    def test_returns_leg(self, strategy):
        leg = strategy.add(23600, "CE", "SELL")
        assert isinstance(leg, Leg)

    def test_instrument_set_correctly(self, strategy):
        leg = strategy.add(23600, "CE", "SELL")
        assert leg.instrument == Instrument(23600, "CE")

    def test_side_and_qty(self, strategy):
        leg = strategy.add(23600, "PE", "BUY", qty=50)
        assert leg.side == "BUY"
        assert leg.qty == 50

    def test_default_qty_is_one(self, strategy):
        leg = strategy.add(23600, "CE", "SELL")
        assert leg.qty == 1


# ─── Strategy.add() — relative strike mode ────────────────────────────────────


class TestRelativeStrikeMode:
    """Tests for relative_strikes=True / strike_step class variables."""

    def _make_ctx(self, atm: int = 23600) -> MockBarContext:
        return MockBarContext(atm=atm)

    def test_default_relative_strikes_is_false(self, strategy):
        assert strategy.relative_strikes is False

    def test_default_strike_step_is_50(self, strategy):
        assert strategy.strike_step == 50

    def test_absolute_mode_unchanged(self, strategy):
        """Default mode: strike value is used as-is."""
        leg = strategy.add(23600, "CE", "SELL")
        assert leg.instrument.strike == 23600

    def test_atm_strike_zero_ce(self, strategy):
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(0, "CE", "SELL")
        assert leg.instrument.strike == 23600

    def test_atm_strike_zero_pe(self, strategy):
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(0, "PE", "SELL")
        assert leg.instrument.strike == 23600

    def test_otm_1_ce(self, strategy):
        """CE: OTM +1 step → atm + step."""
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(1, "CE", "SELL")
        assert leg.instrument.strike == 23650

    def test_otm_1_pe(self, strategy):
        """PE: OTM +1 step → atm - step."""
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(1, "PE", "SELL")
        assert leg.instrument.strike == 23550

    def test_itm_negative_ce(self, strategy):
        """CE: ITM -1 step → atm - step."""
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(-1, "CE", "SELL")
        assert leg.instrument.strike == 23550

    def test_itm_negative_pe(self, strategy):
        """PE: ITM -1 step → atm + step."""
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(-1, "PE", "SELL")
        assert leg.instrument.strike == 23650

    def test_custom_strike_step(self, strategy):
        """BankNifty uses step=100."""
        strategy.relative_strikes = True
        strategy.strike_step = 100
        strategy._ctx = self._make_ctx(atm=51200)
        leg = strategy.add(1, "CE", "SELL")
        assert leg.instrument.strike == 51300

    def test_multiple_steps_otm(self, strategy):
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        leg = strategy.add(3, "CE", "SELL")
        assert leg.instrument.strike == 23750  # 23600 + 3*50

    def test_relative_mode_via_run_one_cycle(self):
        """ctx stored on self._ctx during run_one_cycle is used by add()."""

        class RelativeStrategy(Strategy):
            relative_strikes = True
            strike_step = 50
            last_leg = None

            def can_enter(self, tick, ctx):
                return True

            def on_entry(self, tick, ctx):
                self.last_leg = self.add(1, "CE", "SELL")

            def on_exit_condition(self, tick, ctx):
                return False

        s = RelativeStrategy()
        ctx = MockBarContext(atm=23600)
        s.run_one_cycle("09:15:00", ctx)
        assert s.last_leg.instrument.strike == 23650

    def test_absolute_strike_in_relative_mode_produces_no_fill(self, strategy):
        """
        Misuse: passing an absolute strike (e.g. 23600) in relative mode.
        Resolves to atm + 23600*50 = an absurdly large strike that will never
        have a price in the data → try_fill returns None (no trade entered).
        """
        strategy.relative_strikes = True
        strategy._ctx = self._make_ctx(atm=23600)
        # strike=23600 in relative mode → 23600 + 23600*50 = 1,203,600
        leg = strategy.add(23600, "CE", "SELL")
        ctx = MockBarContext(prices={})  # no prices for any strike
        result = strategy.try_fill([leg], ctx)
        assert result is None  # no fill — instrument doesn't exist

    def test_ctx_updated_each_tick(self):
        """If ATM changes between ticks, add() uses the latest ctx."""

        class RelativeStrategy(Strategy):
            relative_strikes = True
            strike_step = 50
            strikes_seen = []

            def can_enter(self, tick, ctx):
                return True

            def on_entry(self, tick, ctx):
                leg = self.add(0, "CE", "SELL")
                self.strikes_seen.append(leg.instrument.strike)

            def on_exit_condition(self, tick, ctx):
                return False

        s = RelativeStrategy()
        s.run_one_cycle("09:15:00", MockBarContext(atm=23600))
        s.run_one_cycle("09:16:00", MockBarContext(atm=23650))
        assert s.strikes_seen == [23600, 23650]


# ─── Strategy.try_fill() — List mode (auto-key) ───────────────────────────────


class TestTryFillListMode:
    def test_returns_dict_on_success(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        result = strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        assert isinstance(result, dict)
        assert "23600CE" in result
        assert "23600PE" in result

    def test_returns_none_when_any_leg_stale(self, strategy):
        """All-or-nothing: CE live but PE stale → None."""
        ctx = MockBarContext(prices={"23600CE": (100.0, 0), "23600PE": (80.0, 1)})
        result = strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        assert result is None

    def test_returns_none_when_all_legs_stale(self, strategy):
        ctx = stale_ctx("23600CE", "23600PE")
        result = strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        assert result is None

    def test_returns_none_when_no_price(self, strategy):
        ctx = empty_ctx()
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result is None

    def test_trade_entry_price_set(self, strategy):
        ctx = live_ctx("23600CE", price=145.5)
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].entry_price == 145.5

    def test_trade_label_is_auto_key(self, strategy):
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].label == "23600CE"

    def test_trade_cycle_set_from_current_cycle(self, strategy):
        strategy.current_cycle = 1
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].cycle == 1

    def test_trade_tick_and_index_recorded(self, strategy):
        ctx = live_ctx("23600CE", tick="09:30:00", idx=15)
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        t = result["23600CE"]
        assert t.entry_tick == "09:30:00"
        assert t.entry_index == 15

    def test_positions_populated(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        assert "23600CE" in strategy.positions
        assert "23600PE" in strategy.positions

    def test_state_transitions_idle_to_active(self, strategy):
        assert strategy.state == "IDLE"
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert strategy.state == "ACTIVE"

    def test_state_stays_active_on_second_fill(self, strategy):
        """on_adjust may call try_fill — state must stay ACTIVE."""
        ctx = live_ctx("23600CE", "23700CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert strategy.state == "ACTIVE"
        strategy.try_fill([strategy.add(23700, "CE", "SELL")], ctx)
        assert strategy.state == "ACTIVE"

    def test_no_state_change_on_failed_fill(self, strategy):
        """Failed fill must NOT change state."""
        ctx = empty_ctx()
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert strategy.state == "IDLE"

    def test_duplicate_auto_key_raises_value_error(self, strategy):
        """Two legs with same instrument in list → collision."""
        ctx = live_ctx("23600CE")
        with pytest.raises(ValueError, match="23600CE"):
            strategy.try_fill(
                [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "CE", "BUY")],
                ctx,
            )

    def test_key_collision_with_open_position_raises(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        # Try to fill same key again
        with pytest.raises(ValueError, match="23600CE"):
            strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)


# ─── Strategy.try_fill() — Dict mode (user-provided keys) ────────────────────


class TestTryFillDictMode:
    def test_user_keys_in_result(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        result = strategy.try_fill(
            {
                "entry_ce": strategy.add(23600, "CE", "SELL"),
                "entry_pe": strategy.add(23600, "PE", "SELL"),
            },
            ctx,
        )
        assert "entry_ce" in result
        assert "entry_pe" in result

    def test_trade_label_matches_user_key(self, strategy):
        ctx = live_ctx("23600CE")
        result = strategy.try_fill({"my_ce": strategy.add(23600, "CE", "SELL")}, ctx)
        assert result["my_ce"].label == "my_ce"

    def test_returns_none_when_any_stale(self, strategy):
        ctx = MockBarContext(prices={"23600CE": (100.0, 0), "23600PE": (80.0, 2)})
        result = strategy.try_fill(
            {
                "ce": strategy.add(23600, "CE", "SELL"),
                "pe": strategy.add(23600, "PE", "SELL"),
            },
            ctx,
        )
        assert result is None

    def test_key_collision_with_position_raises(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill({"my_ce": strategy.add(23600, "CE", "SELL")}, ctx)
        with pytest.raises(ValueError, match="my_ce"):
            strategy.try_fill({"my_ce": strategy.add(23600, "CE", "SELL")}, ctx)

    def test_different_key_same_instrument_allowed_after_close(self, strategy):
        """Key re-use is allowed once the old trade is closed."""
        ctx = live_ctx("23600CE", "23700CE", tick="09:15:00", idx=0)
        strategy.try_fill({"first_ce": strategy.add(23600, "CE", "SELL")}, ctx)
        strategy.close_trade("first_ce", "09:20:00", 5, ctx, "manual")
        ctx2 = live_ctx("23600CE", tick="09:20:00", idx=5)
        result = strategy.try_fill(
            {"first_ce": strategy.add(23600, "CE", "SELL")}, ctx2
        )
        assert result is not None  # key was freed


# ─── Strategy.open_trades ─────────────────────────────────────────────────────


class TestOpenTrades:
    def test_open_trades_empty_initially(self, strategy):
        assert strategy.open_trades == []

    def test_open_trades_reflects_positions(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        assert len(strategy.open_trades) == 2

    def test_open_trades_decreases_on_close(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "manual")
        assert len(strategy.open_trades) == 1


# ─── Strategy.close_trade() ───────────────────────────────────────────────────


class TestCloseTrade:
    def test_moves_to_closed_trades(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        assert len(strategy.closed_trades) == 1
        assert strategy.closed_trades[0].label == "23600CE"

    def test_removed_from_positions(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        assert "23600CE" not in strategy.positions

    def test_trade_is_closed(self, strategy):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        assert strategy.closed_trades[0].is_open is False

    def test_exit_reason_set(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "my_reason")
        assert strategy.closed_trades[0].exit_reason == "my_reason"

    def test_returns_none_for_unknown_label(self, strategy):
        ctx = empty_ctx()
        result = strategy.close_trade("nonexistent", "09:20:00", 5, ctx, "SL")
        assert result is None

    def test_key_freed_after_close(self, strategy):
        """After close, same label can be used again."""
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        # Re-enter with same key
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result is not None


# ─── Strategy.close_all() ─────────────────────────────────────────────────────


class TestCloseAll:
    def test_closes_all_positions(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        closed = strategy.close_all("09:30:00", 15, ctx, "EOD")
        assert len(closed) == 2
        assert strategy.positions == {}

    def test_all_moved_to_closed_trades(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        strategy.close_all("09:30:00", 15, ctx, "EOD")
        assert len(strategy.closed_trades) == 2

    def test_noop_on_empty_positions(self, strategy):
        ctx = empty_ctx()
        result = strategy.close_all("09:30:00", 15, ctx, "EOD")
        assert result == []

    def test_reason_applied_to_all(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        strategy.close_all("09:30:00", 15, ctx, "my_reason")
        assert all(t.exit_reason == "my_reason" for t in strategy.closed_trades)


# ─── State machine: run_one_cycle() ──────────────────────────────────────────


class TestRunOneCycle:
    def test_done_state_is_noop(self, strategy):
        """DONE state: none of the hooks are called."""
        strategy.state = "DONE"
        ctx = empty_ctx()
        strategy.run_one_cycle("09:15:00", ctx)
        assert strategy.entry_calls == 0
        assert strategy.adjust_calls == 0

    def test_idle_with_can_enter_false_no_entry(self, strategy):
        strategy.can_enter_return = False
        ctx = empty_ctx()
        strategy.run_one_cycle("09:15:00", ctx)
        assert strategy.entry_calls == 0
        assert strategy.state == "IDLE"

    def test_idle_with_can_enter_true_calls_on_entry(self, strategy):
        strategy.can_enter_return = True
        ctx = empty_ctx()
        strategy.run_one_cycle("09:15:00", ctx)
        assert strategy.entry_calls == 1

    def test_successful_fill_transitions_to_active(self, strategy):
        strategy.can_enter_return = True
        strategy.legs_to_fill = [strategy.add(23600, "CE", "SELL")]
        ctx = live_ctx("23600CE")
        strategy.run_one_cycle("09:15:00", ctx)
        assert strategy.state == "ACTIVE"

    def test_failed_fill_stays_idle(self, strategy):
        strategy.can_enter_return = True
        strategy.legs_to_fill = [strategy.add(23600, "CE", "SELL")]
        ctx = empty_ctx()  # no live prices
        strategy.run_one_cycle("09:15:00", ctx)
        assert strategy.state == "IDLE"

    def test_failed_fill_retries_next_tick(self, strategy):
        strategy.can_enter_return = True
        strategy.legs_to_fill = [strategy.add(23600, "CE", "SELL")]
        ctx_fail = empty_ctx(tick="09:15:00", idx=0)
        ctx_live = live_ctx("23600CE", tick="09:16:00", idx=1)
        strategy.run_one_cycle("09:15:00", ctx_fail)
        assert strategy.entry_calls == 1
        strategy.run_one_cycle("09:16:00", ctx_live)
        assert strategy.entry_calls == 2  # retried
        assert strategy.state == "ACTIVE"  # filled on second attempt

    def test_active_state_calls_on_adjust(self, strategy):
        strategy.state = "ACTIVE"
        ctx = empty_ctx()
        strategy.run_one_cycle("09:16:00", ctx)
        assert strategy.adjust_calls == 1

    def test_active_no_exit_signal(self, strategy):
        strategy.state = "ACTIVE"
        strategy.exit_condition = False
        ctx = empty_ctx()
        strategy.run_one_cycle("09:16:00", ctx)
        assert strategy.exit_calls == 0
        assert strategy.state == "ACTIVE"

    def test_active_exit_condition_triggers_exit(self, strategy):
        strategy.state = "ACTIVE"
        strategy.exit_condition = True
        ctx = empty_ctx()
        strategy.run_one_cycle("09:16:00", ctx)
        assert strategy.exit_calls == 1

    def test_exit_then_done_when_max_cycles_1(self, strategy):
        """Default max_cycles=1 → DONE after first exit."""
        strategy.state = "ACTIVE"
        strategy.exit_condition = True
        ctx = empty_ctx()
        strategy.run_one_cycle("09:16:00", ctx)
        assert strategy.state == "DONE"

    def test_adjust_called_before_exit_check(self, strategy):
        """Guaranteed order: on_adjust fires even in the tick that triggers exit."""
        strategy.state = "ACTIVE"
        strategy.exit_condition = True
        ctx = empty_ctx()
        strategy.run_one_cycle("09:16:00", ctx)
        assert strategy.adjust_calls == 1
        assert strategy.exit_calls == 1


# ─── _handle_cycle_done() ────────────────────────────────────────────────────


class TestHandleCycleDone:
    def test_single_cycle_marks_done(self, strategy):
        strategy.max_cycles = 1
        strategy.current_cycle = 0
        strategy._handle_cycle_done()
        assert strategy.state == "DONE"

    def test_multi_cycle_resets_to_idle(self, strategy):
        strategy.max_cycles = 3
        strategy.current_cycle = 0
        strategy._handle_cycle_done()
        assert strategy.state == "IDLE"
        assert strategy.current_cycle == 1

    def test_last_cycle_marks_done(self, strategy):
        strategy.max_cycles = 3
        strategy.current_cycle = 2
        strategy._handle_cycle_done()
        assert strategy.state == "DONE"

    def test_cycle_reset_clears_positions(self, strategy):
        strategy.max_cycles = 2
        strategy.current_cycle = 0
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy._handle_cycle_done()
        # After cycle reset: positions cleared, state IDLE
        assert strategy.positions == {}
        assert strategy.state == "IDLE"

    def test_cycle_reset_preserves_closed_trades(self, strategy):
        """closed_trades must accumulate across cycles."""
        strategy.max_cycles = 2
        strategy.current_cycle = 0
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        assert len(strategy.closed_trades) == 1
        strategy._handle_cycle_done()
        assert len(strategy.closed_trades) == 1  # not wiped


# ─── _eod_force_close() ──────────────────────────────────────────────────────


class TestEodForceClose:
    def test_closes_all_open_positions(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        strategy._eod_force_close("15:29:00", 374, ctx)
        assert strategy.positions == {}
        assert len(strategy.closed_trades) == 2

    def test_reason_is_eod_force(self, strategy):
        ctx = live_ctx("23600CE")
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy._eod_force_close("15:29:00", 374, ctx)
        assert strategy.closed_trades[0].exit_reason == "EOD_FORCE"

    def test_state_becomes_done(self, strategy):
        ctx = empty_ctx()
        strategy._eod_force_close("15:29:00", 374, ctx)
        assert strategy.state == "DONE"

    def test_noop_on_empty_positions(self, strategy):
        """Empty positions — must not crash."""
        ctx = empty_ctx()
        strategy._eod_force_close("15:29:00", 374, ctx)
        assert strategy.positions == {}

    def test_force_close_from_any_state(self, strategy):
        """EOD fires regardless of current state."""
        strategy.state = "IDLE"
        strategy._eod_force_close("15:29:00", 374, empty_ctx())
        assert strategy.state == "DONE"


# ─── _reset_for_new_day() ────────────────────────────────────────────────────


class TestResetForNewDay:
    def test_state_reset_to_idle(self, strategy):
        strategy.state = "DONE"
        strategy._reset_for_new_day()
        assert strategy.state == "IDLE"

    def test_cycle_reset_to_zero(self, strategy):
        strategy.current_cycle = 3
        strategy._reset_for_new_day()
        assert strategy.current_cycle == 0

    def test_positions_cleared(self, strategy):
        # Manually add a fake open position
        strategy.positions["fake"] = MagicMock()
        strategy._reset_for_new_day()
        assert strategy.positions == {}

    def test_closed_trades_not_cleared(self, strategy):
        """closed_trades accumulates across days — must never be wiped."""
        strategy.closed_trades.append(MagicMock())
        strategy._reset_for_new_day()
        assert len(strategy.closed_trades) == 1


# ─── Lookup helpers ───────────────────────────────────────────────────────────


class TestLookupHelpers:
    def _fill_and_close(self, strategy, label, instrument_key, price=100.0):
        ctx = live_ctx(instrument_key, price=price)
        strategy.try_fill({label: strategy.add(23600, "CE", "SELL")}, ctx)
        strategy.close_trade(label, "09:20:00", 5, ctx, "SL")

    def test_get_closed_by_label(self, strategy):
        self._fill_and_close(strategy, "ce_entry", "23600CE")
        result = strategy.get_closed_by_label("ce_entry")
        assert len(result) == 1
        assert result[0].label == "ce_entry"

    def test_get_closed_by_label_empty_if_none(self, strategy):
        assert strategy.get_closed_by_label("missing") == []

    def test_get_closed_by_instrument(self, strategy):
        self._fill_and_close(strategy, "ce1", "23600CE")
        result = strategy.get_closed_by_instrument("23600CE")
        assert len(result) == 1
        assert result[0].instrument == "23600CE"

    def test_get_closed_by_instrument_multiple(self, strategy):
        """Multiple cycles of the same instrument accumulate."""
        strategy.max_cycles = 2
        self._fill_and_close(strategy, "ce1", "23600CE")
        strategy._handle_cycle_done()  # reset cycle
        self._fill_and_close(strategy, "ce1", "23600CE")
        result = strategy.get_closed_by_instrument("23600CE")
        assert len(result) == 2


# ─── position_summary ─────────────────────────────────────────────────────────


class TestPositionSummary:
    def test_empty_positions(self, strategy):
        assert strategy.position_summary == {}

    def test_sell_positions(self, strategy):
        ctx = live_ctx("23600CE", "23600PE")
        strategy.try_fill(
            [strategy.add(23600, "CE", "SELL"), strategy.add(23600, "PE", "SELL")],
            ctx,
        )
        summary = strategy.position_summary
        assert summary.get("23600CE_SELL") == 1
        assert summary.get("23600PE_SELL") == 1

    def test_qty_accumulates(self, strategy):
        """Two trades same instrument+side → qty summed."""
        strategy.max_cycles = 2
        ctx = live_ctx("23600CE", "23700CE")
        strategy.try_fill({"a": strategy.add(23600, "CE", "SELL", qty=2)}, ctx)
        strategy.try_fill({"b": strategy.add(23700, "CE", "SELL", qty=3)}, ctx)
        summary = strategy.position_summary
        assert summary.get("23600CE_SELL") == 2
        assert summary.get("23700CE_SELL") == 3


# ─── unrealized_pnl ──────────────────────────────────────────────────────────


class TestUnrealizedPnl:
    def test_zero_when_no_positions(self, strategy):
        ctx = live_ctx("23600CE")
        assert strategy.unrealized_pnl(ctx) == pytest.approx(0.0)

    def test_sell_loss_when_price_rises(self, strategy):
        """SELL at 100, now at 120 → unrealized PnL = -20."""
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        ctx2 = live_ctx("23600CE", price=120.0)
        assert strategy.unrealized_pnl(ctx2) == pytest.approx(-20.0)

    def test_sell_profit_when_price_falls(self, strategy):
        """SELL at 100, now at 80 → unrealized PnL = +20."""
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        ctx2 = live_ctx("23600CE", price=80.0)
        assert strategy.unrealized_pnl(ctx2) == pytest.approx(20.0)

    def test_buy_profit_when_price_rises(self, strategy):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "BUY")], ctx)
        ctx2 = live_ctx("23600CE", price=115.0)
        assert strategy.unrealized_pnl(ctx2) == pytest.approx(15.0)

    def test_fallback_to_entry_when_no_price(self, strategy):
        """No price data → MTM = 0 for that leg."""
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        ctx_no_data = MockBarContext(prices={})  # no data
        assert strategy.unrealized_pnl(ctx_no_data) == pytest.approx(0.0)


# ─── Strategy.to_dataframe() / save_trades() ─────────────────────────────────


class TestToDataframe:
    def test_empty_returns_empty_dataframe(self, strategy):
        import pandas as pd

        df = strategy.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_closed_trades_in_dataframe(self, strategy):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        df = strategy.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]["is_open"] == False
        assert df.iloc[0]["label"] == "23600CE"

    def test_open_trades_in_dataframe(self, strategy):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        df = strategy.to_dataframe()
        assert len(df) == 1
        assert df.iloc[0]["is_open"] == True

    def test_open_and_closed_combined(self, strategy):
        ctx_ce = live_ctx("23600CE", price=100.0)
        ctx_pe = live_ctx("23600PE", price=80.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx_ce)
        strategy.try_fill([strategy.add(23600, "PE", "SELL")], ctx_pe)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx_ce, "SL")
        df = strategy.to_dataframe()
        assert len(df) == 2
        assert df[df["is_open"] == False]["label"].iloc[0] == "23600CE"
        assert df[df["is_open"] == True]["label"].iloc[0] == "23600PE"

    def test_open_trade_has_null_exit_fields(self, strategy):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        df = strategy.to_dataframe()
        assert df.iloc[0]["exit_tick"] is None
        assert df.iloc[0]["exit_price"] is None


class TestSaveTrades:
    def test_save_csv(self, strategy, tmp_path):
        import pandas as pd

        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        path = tmp_path / "trades.csv"
        strategy.save_trades(path)
        df = pd.read_csv(path)
        assert len(df) == 1
        assert "label" in df.columns
        assert "is_open" in df.columns

    def test_save_parquet(self, strategy, tmp_path):
        import pandas as pd

        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        path = tmp_path / "trades.parquet"
        strategy.save_trades(path)
        df = pd.read_parquet(path)
        assert len(df) == 1
        assert "is_open" in df.columns

    def test_save_feather(self, strategy, tmp_path):
        import pandas as pd

        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.close_trade("23600CE", "09:20:00", 5, ctx, "SL")
        path = tmp_path / "trades.feather"
        strategy.save_trades(path)
        df = pd.read_feather(path)
        assert len(df) == 1
        assert "is_open" in df.columns

    def test_unsupported_extension_raises(self, strategy, tmp_path):
        with pytest.raises(ValueError, match="Unsupported file format"):
            strategy.save_trades(tmp_path / "trades.xlsx")

    def test_accepts_string_path(self, strategy, tmp_path):
        ctx = live_ctx("23600CE", price=100.0)
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        strategy.save_trades(str(tmp_path / "trades.csv"))


# ─── Strategy.add() — kwargs → Leg.meta ──────────────────────────────────────


class TestAddKwargs:
    def test_no_kwargs_gives_empty_meta(self, strategy):
        """add() without extra kwargs → Leg.meta is empty."""
        leg = strategy.add(23600, "CE", "SELL")
        assert leg.meta == {}

    def test_single_kwarg_stored_in_meta(self, strategy):
        leg = strategy.add(23600, "CE", "SELL", strikes_away=2)
        assert leg.meta["strikes_away"] == 2

    def test_multiple_kwargs_stored_in_meta(self, strategy):
        leg = strategy.add(23600, "CE", "SELL", strikes_away=2, tag="straddle")
        assert leg.meta["strikes_away"] == 2
        assert leg.meta["tag"] == "straddle"

    def test_qty_not_captured_as_meta(self, strategy):
        """qty is a named param — must not bleed into meta."""
        leg = strategy.add(23600, "CE", "SELL", qty=2)
        assert "qty" not in leg.meta
        assert leg.qty == 2

    def test_kwargs_not_shared_between_legs(self, strategy):
        """Each add() call produces an independent meta dict."""
        leg_a = strategy.add(23600, "CE", "SELL", tag="ce")
        leg_b = strategy.add(23600, "PE", "SELL", tag="pe")
        assert leg_a.meta["tag"] == "ce"
        assert leg_b.meta["tag"] == "pe"


# ─── try_fill() metadata capture ─────────────────────────────────────────────


class TestTryFillMetadata:
    def test_stamps_trade_date_from_strategy(self, strategy):
        """trade_date on Trade is populated from strategy.trade_date."""
        strategy.trade_date = "2025-01-15"
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].trade_date == "2025-01-15"

    def test_trade_date_empty_when_strategy_date_not_set(self, strategy):
        """trade_date defaults to empty string if strategy.trade_date is unset."""
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].trade_date == ""

    def test_leg_kwargs_copied_to_trade_metadata(self, strategy):
        """Leg.meta items (from add kwargs) appear in trade.metadata (no prefix)."""
        ctx = live_ctx("23600CE")
        leg = strategy.add(23600, "CE", "SELL", strikes_away=2, tag="straddle")
        result = strategy.try_fill([leg], ctx)
        trade = result["23600CE"]
        assert trade.metadata["strikes_away"] == 2
        assert trade.metadata["tag"] == "straddle"

    def test_leg_kwargs_per_leg_in_dict_mode(self, strategy):
        """In dict mode, each leg's meta is copied to its own Trade."""
        ctx = MockBarContext(prices={"23600CE": (100.0, 0), "23600PE": (80.0, 0)})
        result = strategy.try_fill(
            {
                "ce": strategy.add(23600, "CE", "SELL", tag="ce_leg"),
                "pe": strategy.add(23600, "PE", "SELL", tag="pe_leg"),
            },
            ctx,
        )
        assert result["ce"].metadata["tag"] == "ce_leg"
        assert result["pe"].metadata["tag"] == "pe_leg"

    def test_captures_entry_info_attributes_from_bar(self, strategy):
        """entry_<attr> stamped from ctx.get_bar() for each info_attribute."""
        strategy.engine = MockEngine(info_attributes=["iv", "delta"])
        bar = {"close": 100.0, "iv": 0.18, "delta": -0.45, "volume": 500.0}
        ctx = MockBarContext(
            tick="09:15:00",
            tick_index=0,
            prices={"23600CE": (100.0, 0)},
            bars={"23600CE": (bar, 0)},
        )
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        trade = result["23600CE"]
        assert trade.metadata["entry_iv"] == pytest.approx(0.18)
        assert trade.metadata["entry_delta"] == pytest.approx(-0.45)

    def test_entry_attr_none_when_bar_missing(self, strategy):
        """entry_<attr> is None when ctx.get_bar() returns no data."""
        strategy.engine = MockEngine(info_attributes=["iv"])
        ctx = live_ctx("23600CE")  # no bars dict → get_bar returns (None, -1)
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].metadata["entry_iv"] is None

    def test_entry_attr_none_when_column_not_in_bar(self, strategy):
        """entry_<attr> is None when bar exists but column is absent."""
        strategy.engine = MockEngine(info_attributes=["iv"])
        bar = {"close": 100.0, "volume": 500.0}  # no 'iv'
        ctx = MockBarContext(
            prices={"23600CE": (100.0, 0)},
            bars={"23600CE": (bar, 0)},
        )
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result["23600CE"].metadata["entry_iv"] is None

    def test_no_info_capture_when_engine_is_none(self, strategy):
        """When engine=None (unit‐test isolation), no entry_ keys are added."""
        strategy.engine = None
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        trade = result["23600CE"]
        assert not any(k.startswith("entry_") for k in trade.metadata)

    def test_no_info_capture_when_info_attributes_empty(self, strategy):
        """Empty info_attributes → no entry_ keys in metadata."""
        strategy.engine = MockEngine(info_attributes=[])
        ctx = live_ctx("23600CE")
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert not any(k.startswith("entry_") for k in result["23600CE"].metadata)

    def test_failed_fill_does_not_capture_metadata(self, strategy):
        """If try_fill returns None (stale price), no metadata is stamped."""
        strategy.engine = MockEngine(info_attributes=["iv"])
        ctx = stale_ctx("23600CE")  # lag > 0 → fill fails
        result = strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        assert result is None
        assert strategy.closed_trades == []


# ─── close_trade() metadata capture ──────────────────────────────────────────


class TestCloseTradeMetadata:
    def _setup_open_trade(self, strategy, bar_at_entry=None):
        """Helper: fill one CE trade with optional bar data at entry."""
        strategy.engine = MockEngine(info_attributes=["iv"])
        entry_bar = bar_at_entry or {"close": 100.0, "iv": 0.18}
        ctx = MockBarContext(
            tick="09:15:00",
            tick_index=0,
            prices={"23600CE": (100.0, 0)},
            bars={"23600CE": (entry_bar, 0)},
        )
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        return ctx

    def test_captures_exit_info_attributes(self, strategy):
        """exit_<attr> stamped from ctx.get_bar() when trade is closed."""
        self._setup_open_trade(strategy)
        exit_bar = {"close": 80.0, "iv": 0.14}
        ctx_exit = MockBarContext(
            tick="10:00:00",
            tick_index=15,
            prices={"23600CE": (80.0, 0)},
            bars={"23600CE": (exit_bar, 0)},
        )
        trade = strategy.close_trade("23600CE", "10:00:00", 15, ctx_exit)
        assert trade.metadata["exit_iv"] == pytest.approx(0.14)

    def test_entry_attrs_still_present_after_close(self, strategy):
        """entry_ attrs from try_fill are still in metadata after close."""
        self._setup_open_trade(strategy, bar_at_entry={"close": 100.0, "iv": 0.18})
        exit_bar = {"close": 80.0, "iv": 0.14}
        ctx_exit = MockBarContext(
            tick="10:00:00",
            tick_index=15,
            prices={"23600CE": (80.0, 0)},
            bars={"23600CE": (exit_bar, 0)},
        )
        trade = strategy.close_trade("23600CE", "10:00:00", 15, ctx_exit)
        assert trade.metadata["entry_iv"] == pytest.approx(0.18)
        assert trade.metadata["exit_iv"] == pytest.approx(0.14)

    def test_exit_attr_none_when_bar_missing_at_close(self, strategy):
        """exit_<attr> is None when get_bar() returns no data at exit."""
        self._setup_open_trade(strategy)
        ctx_exit = MockBarContext(
            tick="10:00:00",
            tick_index=15,
            prices={"23600CE": (80.0, 0)},
            # no bars → get_bar returns (None, -1)
        )
        trade = strategy.close_trade("23600CE", "10:00:00", 15, ctx_exit)
        assert trade.metadata["exit_iv"] is None

    def test_no_exit_capture_when_engine_is_none(self, strategy):
        """When engine=None, no exit_ keys added on close."""
        ctx = live_ctx("23600CE", price=100.0)
        strategy.engine = None
        strategy.try_fill([strategy.add(23600, "CE", "SELL")], ctx)
        trade = strategy.close_trade("23600CE", "10:00:00", 15, ctx)
        assert not any(k.startswith("exit_") for k in trade.metadata)

    def test_to_dataframe_includes_metadata_columns(self, strategy):
        """entry_/exit_ attrs and leg kwargs all appear as DataFrame columns."""
        import pandas as pd

        strategy.engine = MockEngine(info_attributes=["iv"])
        strategy.trade_date = "2025-01-15"
        bar = {"close": 100.0, "iv": 0.18}
        ctx_in = MockBarContext(
            prices={"23600CE": (100.0, 0)},
            bars={"23600CE": (bar, 0)},
        )
        strategy.try_fill([strategy.add(23600, "CE", "SELL", strikes_away=0)], ctx_in)
        exit_bar = {"close": 80.0, "iv": 0.12}
        ctx_out = MockBarContext(
            prices={"23600CE": (80.0, 0)},
            bars={"23600CE": (exit_bar, 0)},
        )
        strategy.close_trade("23600CE", "10:00:00", 15, ctx_out)

        df = strategy.to_dataframe()
        assert "trade_date" in df.columns
        assert "entry_iv" in df.columns
        assert "exit_iv" in df.columns
        assert "strikes_away" in df.columns
        assert df.iloc[0]["trade_date"] == "2025-01-15"
        assert df.iloc[0]["entry_iv"] == pytest.approx(0.18)
        assert df.iloc[0]["exit_iv"] == pytest.approx(0.12)
        assert df.iloc[0]["strikes_away"] == 0
