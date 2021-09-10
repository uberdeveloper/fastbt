import pytest
import pendulum
import random
from fastbt.models.breakout import Breakout, StockData, HighLow
from fastbt.brokers.zerodha import Zerodha
from pydantic import ValidationError
from unittest.mock import Mock, patch, call


@pytest.fixture
def base_breakout():
    return Breakout(
        symbols=["GOOG", "AAPL"], instrument_map={"GOOG": 1010, "AAPL": 2100}
    )


@pytest.fixture
def sl_breakout():
    ts = Breakout(
        symbols=["GOOG", "AAPL", "INTL"],
        instrument_map={"GOOG": 1010, "AAPL": 2100, "INTL": 3000},
    )
    ts.update_high_low(
        [
            HighLow(symbol="AAPL", high=101, low=98),
            HighLow(symbol="GOOG", high=104, low=100),
            HighLow(symbol="INTL", high=302, low=295),
        ]
    )
    ts._data["AAPL"].ltp = 100
    ts._data["GOOG"].ltp = 104
    ts._data["INTL"].ltp = 300
    return ts


@pytest.fixture
def live_order():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        ts = Breakout(
            symbols=["GOOG", "AAPL", "INTL"],
            instrument_map={"GOOG": 1010, "AAPL": 2100, "INTL": 3000},
            broker=broker,
            env="live",
        )
        ts.update_high_low(
            [
                HighLow(symbol="AAPL", high=101, low=98),
                HighLow(symbol="GOOG", high=104, low=100),
                HighLow(symbol="INTL", high=302, low=295),
            ]
        )
        ts._data["AAPL"].ltp = 100
        ts._data["INTL"].ltp = 300
        return ts


def test_breakout_parent_defaults(base_breakout):
    ts = base_breakout
    assert ts.SYSTEM_START_TIME == pendulum.today(tz="Asia/Kolkata").add(
        hours=9, minutes=15
    )
    assert ts.SYSTEM_END_TIME == pendulum.today(tz="Asia/Kolkata").add(
        hours=15, minutes=15
    )
    assert ts.env == "paper"
    assert ts.done is False


def test_stock_data(base_breakout):
    ts = base_breakout
    assert len(ts.data) == 2
    my_data = {
        "GOOG": StockData(name="GOOG", token=1010),
        "AAPL": StockData(name="AAPL", token=2100),
    }
    assert ts.data == my_data
    assert ts.data["GOOG"].high is None
    assert ts.data["AAPL"].low is None


def test_rev_map(base_breakout):
    ts = base_breakout
    assert ts._rev_map == {1010: "GOOG", 2100: "AAPL"}


def test_high_low(base_breakout):
    ts = base_breakout
    ts.update_high_low(
        [
            HighLow(symbol="AAPL", high=150, low=120),
            HighLow(symbol="GOOG", high=150, low=120),
        ]
    )
    assert ts.data["AAPL"].high == 150
    assert ts.data["GOOG"].low == 120


def test_high_low_dict(base_breakout):
    ts = base_breakout
    ts.update_high_low([{"symbol": "AAPL", "high": 150, "low": 120}])
    assert ts.data["AAPL"].high == 150


def test_high_low_dict_extra_values(base_breakout):
    ts = base_breakout
    ts.update_high_low([{"symbol": "AAPL", "high": 150, "low": 120, "open": 160}])
    assert ts.data["AAPL"].high == 150


def test_high_low_dict_no_symbols(base_breakout):
    ts = base_breakout
    ts.update_high_low([{"symbol": "DOW", "high": 150, "low": 120, "open": 160}])
    assert ts.data["AAPL"].high is None
    assert ts.data["GOOG"].low is None


def test_high_low_no_data_raise_error(base_breakout):
    ts = base_breakout
    with pytest.raises(ValidationError):
        ts.update_high_low([{"symbol": "AAPL", "high": 15}])


def test_stop_loss_default(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss("AAPL", "BUY")
    assert sl == 98
    sl = ts.stop_loss("INTL", "SELL")
    assert sl == 302


def test_stop_loss_value(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss("AAPL", "BUY")
    assert sl == 98
    sl = ts.stop_loss("AAPL", "BUY", method="value")
    assert sl == 100
    sl = ts.stop_loss("AAPL", "BUY", method="value", stop=1)
    assert sl == 99
    sl = ts.stop_loss("GOOG", "SELL", method="value", stop=1)
    assert sl == 105


def test_stop_loss_percentage(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss("AAPL", "BUY")
    assert sl == 98
    sl = ts.stop_loss("AAPL", "BUY", method="percent")
    assert sl == 100
    sl = ts.stop_loss("AAPL", "BUY", method="percent", stop=1.5)
    assert sl == 98.5
    sl = ts.stop_loss("INTL", "SELL", method="percent", stop=3)
    assert sl == 309


def test_stop_loss_no_symbol(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss("SOME", "BUY")
    assert sl == 0


def test_stop_loss_unknown_method(sl_breakout):
    ts = sl_breakout
    sl = ts.stop_loss("AAPL", "BUY", method="unknown")
    assert sl == 98


def test_fetch(base_breakout):
    ts = base_breakout
    ts.fetch(
        [
            {"instrument_token": 1010, "last_price": 118.4},
            {"instrument_token": 2100, "last_price": 218.4},
        ]
    )
    assert ts.data["AAPL"].ltp == 218.4


def test_fetch_no_symbol(base_breakout):
    ts = base_breakout
    ts.fetch(
        [
            {"instrument_token": 1011, "last_price": 118.4},
            {"instrument_token": 2100, "last_price": 218.4},
        ]
    )
    assert ts.data["AAPL"].ltp == 218.4
    assert ts.data["GOOG"].ltp == 0


def test_entry_buy(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    assert ts.data["AAPL"].can_trade is False
    assert ts.data["AAPL"].positions == 985


def test_entry_sell(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 97.9
    ts.run()
    assert ts.data["AAPL"].can_trade is False
    assert ts.data["AAPL"].positions == -1021


def test_dont_trade_when_can_trade_false(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 101.5
    ts._data["AAPL"].can_trade = False
    ts.run()
    assert ts.data["AAPL"].positions == 0


def test_dont_trade_when_positions_not_zero(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 101.5
    ts._data["AAPL"].positions = 36
    ts.run()
    assert ts.data["AAPL"].positions == 36
    assert ts.data["AAPL"].can_trade is True


def test_entry_multiple_symbols(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 101.5
    ts._data["GOOG"].ltp = 99.9
    ts._data["INTL"].ltp = 302
    ts.run()
    assert ts.data["AAPL"].positions == 985
    assert ts.data["GOOG"].positions == -1001
    # No trades since prices are equal
    assert ts.data["INTL"].positions == 0

    ts._data["INTL"].ltp = 302.0005
    ts.run()
    assert ts.data["INTL"].positions == 331


def test_open_positions(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].ltp = 101.5
    ts._data["GOOG"].ltp = 99.9
    ts._data["INTL"].ltp = 302
    ts.run()
    assert ts.open_positions == 2


def test_open_positions_can_trade(sl_breakout):
    ts = sl_breakout
    ts._data["AAPL"].can_trade = False
    ts._data["AAPL"].positions = 0
    ts.run()
    assert ts.open_positions == 1


def test_order_live(live_order):
    ts = live_order
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    assert ts.broker.order_place.call_count == 2
    assert ts.data.get("AAPL").positions == 985
    assert ts.data.get("AAPL").can_trade is False


def test_order_live_multiple_runs(live_order):
    ts = live_order
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    for i in range(10):
        ts.run()
    assert ts.broker.order_place.call_count == 2


def test_order_live_args(live_order):
    ts = live_order
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    kwargs = dict(
        symbol="AAPL", order_type="LIMIT", side="BUY", price=101.5, quantity=985
    )
    assert ts.broker.order_place.call_args_list[0] == call(**kwargs)
    kwargs = dict(
        symbol="AAPL",
        order_type="SL-M",
        side="SELL",
        trigger_price=98.45,
        price=101.5,
        quantity=985,
    )
    assert ts.broker.order_place.call_args_list[-1] == call(**kwargs)
    for i in range(10):
        ts.run()
    assert ts.broker.order_place.call_count == 2


def test_order_live_update_order_id(live_order):
    ts = live_order
    ts.broker.order_place.return_value = 111111
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    assert ts.data["AAPL"].order_id == 111111
    assert ts.data["AAPL"].stop_id == 111111


def test_order_live_kwargs(live_order):
    ts = live_order
    ts._data["AAPL"].ltp = 101.5
    ts.ORDER_DEFAULT_KWARGS = {"exchange": "NYSE", "validity": "DAY", "product": "MIS"}
    ts.run()
    kwargs = dict(
        symbol="AAPL",
        order_type="LIMIT",
        side="BUY",
        price=101.5,
        quantity=985,
        exchange="NYSE",
        validity="DAY",
        product="MIS",
    )
    assert ts.broker.order_place.call_args_list[0] == call(**kwargs)
    kwargs = dict(
        symbol="AAPL",
        order_type="SL-M",
        side="SELL",
        trigger_price=98.45,
        price=101.5,
        quantity=985,
        exchange="NYSE",
        validity="DAY",
        product="MIS",
    )
    assert ts.broker.order_place.call_args_list[-1] == call(**kwargs)


def test_max_positions(sl_breakout):
    ts = sl_breakout
    ts.MAX_POSITIONS = 1
    ts._data["AAPL"].ltp = 101.5
    ts.run()
    ts._data["GOOG"].ltp = 99.9
    ts._data["INTL"].ltp = 303
    ts.run()
    assert ts.open_positions == 1

    ts.MAX_POSITIONS = 2
    ts.run()
    assert ts.open_positions == 3
