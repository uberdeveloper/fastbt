"""
Tests for fastbt.backtest.models — Instrument, Leg, Trade.
Run with: uv run pytest tests/backtest/test_models.py -v
"""
import pytest
from dataclasses import FrozenInstanceError

from fastbt.backtest.models import Instrument, Leg, Trade


# ─── Instrument ───────────────────────────────────────────────────────────────


class TestInstrument:
    def test_key_ce(self):
        inst = Instrument(strike=23600, opt_type="CE")
        assert inst.key() == "23600CE"

    def test_key_pe(self):
        inst = Instrument(strike=23600, opt_type="PE")
        assert inst.key() == "23600PE"

    def test_key_different_strike(self):
        assert Instrument(strike=23650, opt_type="CE").key() == "23650CE"

    def test_frozen_cannot_mutate(self):
        """Instrument is immutable — safe as dict key."""
        inst = Instrument(strike=23600, opt_type="CE")
        with pytest.raises((FrozenInstanceError, TypeError)):
            inst.strike = 23700  # type: ignore

    def test_hashable_as_dict_key(self):
        """Frozen dataclasses are hashable — usable as cache keys."""
        inst = Instrument(strike=23600, opt_type="CE")
        d = {inst: "some_value"}
        assert d[inst] == "some_value"

    def test_equality(self):
        """Same strike + opt_type → equal."""
        a = Instrument(23600, "CE")
        b = Instrument(23600, "CE")
        assert a == b

    def test_inequality_strike(self):
        assert Instrument(23600, "CE") != Instrument(23650, "CE")

    def test_inequality_opt_type(self):
        assert Instrument(23600, "CE") != Instrument(23600, "PE")

    def test_repr(self):
        inst = Instrument(23600, "CE")
        assert "23600CE" in repr(inst)


# ─── Leg ──────────────────────────────────────────────────────────────────────


class TestLeg:
    def test_basic_creation(self):
        inst = Instrument(23600, "CE")
        leg = Leg(instrument=inst, side="SELL", qty=1)
        assert leg.instrument == inst
        assert leg.side == "SELL"
        assert leg.qty == 1

    def test_default_qty(self):
        leg = Leg(instrument=Instrument(23600, "CE"), side="BUY")
        assert leg.qty == 1

    def test_buy_side(self):
        leg = Leg(instrument=Instrument(23600, "PE"), side="BUY", qty=2)
        assert leg.side == "BUY"
        assert leg.qty == 2

    def test_sell_side(self):
        leg = Leg(instrument=Instrument(23600, "PE"), side="SELL", qty=50)
        assert leg.side == "SELL"
        assert leg.qty == 50


# ─── Trade ────────────────────────────────────────────────────────────────────


def make_trade(
    label="23600CE",
    instrument="23600CE",
    side="SELL",
    qty=1,
    cycle=0,
    entry_tick="09:30:00",
    entry_index=15,
    entry_price=100.0,
) -> Trade:
    """Factory helper — creates an open Trade with sane defaults."""
    return Trade(
        label=label,
        instrument=instrument,
        side=side,
        qty=qty,
        cycle=cycle,
        entry_tick=entry_tick,
        entry_index=entry_index,
        entry_price=entry_price,
    )


class TestTradeCreation:
    def test_required_fields(self):
        t = make_trade()
        assert t.label == "23600CE"
        assert t.instrument == "23600CE"
        assert t.side == "SELL"
        assert t.qty == 1
        assert t.cycle == 0
        assert t.entry_tick == "09:30:00"
        assert t.entry_index == 15
        assert t.entry_price == 100.0

    def test_exit_fields_default_none(self):
        t = make_trade()
        assert t.exit_tick is None
        assert t.exit_index is None
        assert t.exit_price is None
        assert t.exit_reason is None

    def test_pnl_defaults_zero(self):
        t = make_trade()
        assert t.gross_pnl == 0.0
        assert t.transaction_cost == 0.0
        assert t.net_pnl == 0.0

    def test_is_open_true_when_no_exit(self):
        t = make_trade()
        assert t.is_open is True

    def test_metadata_default_empty_dict(self):
        t = make_trade()
        assert t.metadata == {}

    def test_metadata_not_shared_between_instances(self):
        """dataclass field(default_factory=dict) must not share state."""
        t1 = make_trade()
        t2 = make_trade()
        t1.metadata["key"] = "value"
        assert "key" not in t2.metadata

    def test_cycle_field(self):
        t = make_trade(cycle=2)
        assert t.cycle == 2

    def test_entry_tick_any_type(self):
        """Clock ticks can be integers, not just time strings."""
        t = make_trade(entry_tick=42, entry_index=42)
        assert t.entry_tick == 42


class TestTradeClose:
    def test_is_open_false_after_close(self):
        t = make_trade(side="SELL", entry_price=100.0)
        t.close(exit_tick="10:00:00", exit_index=45, exit_price=80.0, reason="SL")
        assert t.is_open is False

    def test_exit_fields_populated(self):
        t = make_trade()
        t.close("10:00:00", 45, 80.0, "SL")
        assert t.exit_tick == "10:00:00"
        assert t.exit_index == 45
        assert t.exit_price == 80.0
        assert t.exit_reason == "SL"

    # ── PnL: SELL side ──────────────────────────────────────────────

    def test_sell_profit(self):
        """Sell at 100, exit at 80 → profit of 20."""
        t = make_trade(side="SELL", entry_price=100.0, qty=1)
        t.close("10:00", 45, 80.0, "SL")
        assert t.gross_pnl == pytest.approx(20.0)

    def test_sell_loss(self):
        """Sell at 100, exit at 130 → loss of 30."""
        t = make_trade(side="SELL", entry_price=100.0, qty=1)
        t.close("10:00", 45, 130.0, "SL")
        assert t.gross_pnl == pytest.approx(-30.0)

    def test_sell_breakeven(self):
        t = make_trade(side="SELL", entry_price=100.0)
        t.close("10:00", 45, 100.0, "EOD")
        assert t.gross_pnl == pytest.approx(0.0)

    # ── PnL: BUY side ───────────────────────────────────────────────

    def test_buy_profit(self):
        """Buy at 100, exit at 130 → profit of 30."""
        t = make_trade(side="BUY", entry_price=100.0, qty=1)
        t.close("10:00", 45, 130.0, "target")
        assert t.gross_pnl == pytest.approx(30.0)

    def test_buy_loss(self):
        """Buy at 100, exit at 80 → loss of 20."""
        t = make_trade(side="BUY", entry_price=100.0, qty=1)
        t.close("10:00", 45, 80.0, "SL")
        assert t.gross_pnl == pytest.approx(-20.0)

    # ── Quantity scaling ─────────────────────────────────────────────

    def test_pnl_scales_with_qty(self):
        """Profit should scale linearly with quantity."""
        t = make_trade(side="SELL", entry_price=100.0, qty=50)
        t.close("10:00", 45, 80.0, "SL")
        assert t.gross_pnl == pytest.approx(20.0 * 50)

    # ── Transaction costs ──────────────────────────────────────────

    def test_no_transaction_cost_by_default(self):
        t = make_trade(entry_price=100.0)
        t.close("10:00", 45, 80.0, "SL")
        assert t.transaction_cost == pytest.approx(0.0)
        assert t.net_pnl == pytest.approx(t.gross_pnl)

    def test_transaction_cost_calculated(self):
        """Cost = (entry + exit) * qty * pct / 100."""
        t = make_trade(side="SELL", entry_price=100.0, qty=1)
        t.close("10:00", 45, 80.0, "SL", transaction_cost_pct=0.1)
        # entry_cost = 100 * 1 * 0.1 / 100 = 0.10
        # exit_cost  =  80 * 1 * 0.1 / 100 = 0.08
        # total_cost = 0.18
        assert t.transaction_cost == pytest.approx(0.18)

    def test_net_pnl_equals_gross_minus_cost(self):
        t = make_trade(side="SELL", entry_price=100.0, qty=1)
        t.close("10:00", 45, 80.0, "SL", transaction_cost_pct=0.1)
        assert t.net_pnl == pytest.approx(t.gross_pnl - t.transaction_cost)

    def test_net_pnl_sell_profit_with_cost(self):
        """Sell at 100, exit at 80, cost 0.18 → net = 20 - 0.18 = 19.82."""
        t = make_trade(side="SELL", entry_price=100.0, qty=1)
        t.close("10:00", 45, 80.0, "SL", transaction_cost_pct=0.1)
        assert t.net_pnl == pytest.approx(19.82)

    def test_transaction_cost_scales_with_qty(self):
        t = make_trade(side="SELL", entry_price=100.0, qty=50)
        t.close("10:00", 45, 80.0, "SL", transaction_cost_pct=0.1)
        # entry_cost = 100 * 50 * 0.1 / 100 = 5.0
        # exit_cost  =  80 * 50 * 0.1 / 100 = 4.0
        assert t.transaction_cost == pytest.approx(9.0)

    # ── Tick-counter slippage tracking ───────────────────────────────

    def test_entry_exit_index_preserved(self):
        """tick_index values are preserved intact for slippage analysis."""
        t = make_trade(entry_index=10)
        t.close("10:00", exit_index=15, exit_price=80.0, reason="SL")
        assert t.entry_index == 10
        assert t.exit_index == 15


class TestTradeToDict:
    def test_to_dict_has_required_keys(self):
        t = make_trade()
        t.close("10:00", 45, 80.0, "SL")
        d = t.to_dict()
        required = {
            "label", "instrument", "side", "qty", "cycle",
            "entry_tick", "entry_index", "entry_price",
            "exit_tick", "exit_index", "exit_price", "exit_reason",
            "gross_pnl", "transaction_cost", "net_pnl",
        }
        assert required.issubset(d.keys())

    def test_to_dict_values_correct(self):
        t = make_trade(side="SELL", entry_price=100.0)
        t.close("10:00", 45, 80.0, "SL")
        d = t.to_dict()
        assert d["instrument"] == "23600CE"
        assert d["side"] == "SELL"
        assert d["entry_price"] == 100.0
        assert d["exit_price"] == 80.0
        assert d["gross_pnl"] == pytest.approx(20.0)

    def test_to_dict_includes_metadata(self):
        t = make_trade()
        t.metadata["tag"] = "straddle_leg"
        d = t.to_dict()
        assert d["tag"] == "straddle_leg"

    def test_to_dict_open_trade(self):
        """to_dict works on open trade — exit fields are None."""
        t = make_trade()
        d = t.to_dict()
        assert d["exit_tick"] is None
        assert d["exit_price"] is None
        assert d["gross_pnl"] == 0.0
