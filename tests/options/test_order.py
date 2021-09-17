import pytest
from unittest.mock import patch, call
from fastbt.options.order import *
from fastbt.Meta import Broker
from collections import Counter
import pendulum
from copy import deepcopy
from fastbt.brokers.zerodha import Zerodha


@pytest.fixture
def simple_compound_order():
    com = CompoundOrder(broker=Broker())
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        filled_quantity=20,
        average_price=920,
        status="COMPLETE",
        order_id="aaaaaa",
    )
    com.add_order(
        symbol="goog",
        quantity=10,
        side="sell",
        filled_quantity=10,
        average_price=338,
        status="COMPLETE",
        order_id="bbbbbb",
    )
    com.add_order(
        symbol="aapl",
        quantity=12,
        side="sell",
        filled_quantity=9,
        average_price=975,
        order_id="cccccc",
    )
    return com


@pytest.fixture
def compound_order_average_prices():
    com = CompoundOrder(broker=Broker())
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        order_id="111111",
        filled_quantity=20,
        average_price=1000,
    )
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        order_id="222222",
        filled_quantity=20,
        average_price=900,
    )
    com.add_order(
        symbol="goog",
        quantity=20,
        side="sell",
        order_id="333333",
        filled_quantity=20,
        average_price=700,
    )
    com.add_order(
        symbol="goog",
        quantity=15,
        side="sell",
        order_id="444444",
        filled_quantity=15,
        average_price=600,
    )
    return com


@pytest.fixture
def stop_order():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        stop_order = StopOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type="LIMIT",
            trigger_price=850,
            broker=broker,
        )
        return stop_order


@pytest.fixture
def bracket_order():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        bracket_order = BracketOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type="LIMIT",
            trigger_price=850,
            broker=broker,
            target=960,
        )
    return bracket_order


def test_order_simple():
    order = Order(symbol="aapl", side="buy", quantity=10,
    timezone='Europe/Paris')
    assert order.quantity == 10
    assert order.pending_quantity == 10
    assert order.filled_quantity == 0
    assert order.timestamp is not None
    assert order.internal_id is not None
    assert order.timezone == 'Europe/Paris'


def test_order_is_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_complete is False
    order.filled_quantity = 10
    assert order.is_complete is True


def test_order_is_complete_other_cases():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 6
    assert order.is_complete is False
    order.cancelled_quantity = 4
    assert order.is_complete is True


def test_order_is_pending():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_pending is True
    order.filled_quantity = 10
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5, 5
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5, 4
    assert order.is_pending is True
    order.status = "COMPLETE"
    assert order.is_pending is False


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ((15134,), 15100),
        ((15134, 0, 50), 15150),
        ((15176, 0, 50), 15200),
    ],
)
def test_get_option(test_input, expected):
    print(test_input)
    assert get_option(*test_input) == expected


def test_order_update_simple():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "exchange_order_id": "abcd"}
    )
    assert order.filled_quantity == 7
    assert order.average_price == 912
    assert order.exchange_order_id == "abcd"


def test_order_update_non_attribute():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "message": "not in attributes"}
    )
    assert order.filled_quantity == 7
    assert hasattr(order, "message") is False


def test_order_update_do_not_update_when_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 10
    order.update({"average_price": 912})
    assert order.average_price == 0
    order.filled_quantity = 7
    order.update({"average_price": 912})
    assert order.average_price == 912
    order.average_price = 0
    # This is wrong; this should never be updated directly
    order.status = "COMPLETE"
    assert order.average_price == 0
    assert order.filled_quantity == 7


def test_compound_order_count(simple_compound_order):
    order = simple_compound_order
    assert order.count == 3


def test_compound_order_positions(simple_compound_order):
    order = simple_compound_order
    assert order.positions == Counter({"aapl": 11, "goog": -10})
    order.add_order(symbol="boe", side="buy", quantity=5, filled_quantity=5)
    assert order.positions == Counter({"aapl": 11, "goog": -10, "boe": 5})


def test_compound_order_add_order():
    order = CompoundOrder(broker=Broker())
    order.add_order(symbol="aapl", quantity=5, side="buy", filled_quantity=5)
    order.add_order(symbol="aapl", quantity=4, side="buy", filled_quantity=4)
    assert order.count == 2
    assert order.positions == Counter({"aapl": 9})


def test_compound_order_average_buy_price(compound_order_average_prices):
    order = compound_order_average_prices
    assert order.average_buy_price == dict(aapl=950)


def test_compound_order_average_sell_price(compound_order_average_prices):
    order = compound_order_average_prices
    # Rounding to match significane
    dct = order.average_sell_price
    for k, v in dct.items():
        dct[k] = round(v, 2)
    assert dct == dict(goog=657.14)


def test_compound_order_update_orders(simple_compound_order):
    order = simple_compound_order
    order_data = {
        "aaaaaa": {
            "order_id": "aaaaaa",
            "exchange_order_id": "hexstring",
            "price": 134,
            "average_price": 134,
        },
        "cccccc": {
            "order_id": "cccccc",
            "filled_quantity": 12,
            "status": "COMPLETE",
            "average_price": 180,
            "exchange_order_id": "some_exchange_id",
        },
    }
    updates = order.update_orders(order_data)
    assert updates == {"aaaaaa": False, "bbbbbb": False, "cccccc": True}
    assert order.orders[-1].filled_quantity == 12
    assert order.orders[-1].status == "COMPLETE"
    assert order.orders[-1].average_price == 180
    assert order.orders[-1].exchange_order_id == "some_exchange_id"


def test_compound_order_buy_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.buy_quantity == {"aapl": 20}


def test_compound_order_sell_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.sell_quantity == {"goog": 10, "aapl": 9}


def test_compound_order_update_ltp(simple_compound_order):
    order = simple_compound_order
    assert order.ltp == {}
    assert order.update_ltp({"amzn": 300, "goog": 350}) == {"amzn": 300, "goog": 350}
    order.update_ltp({"aapl": 600})
    assert order.ltp == {"amzn": 300, "goog": 350, "aapl": 600}
    assert order.update_ltp({"goog": 365}) == {"amzn": 300, "goog": 365, "aapl": 600}


def test_compound_order_net_value(simple_compound_order, compound_order_average_prices):
    order = simple_compound_order
    order2 = compound_order_average_prices
    order._orders.extend(order2.orders)
    assert order.net_value == Counter({"aapl": 47625, "goog": -26380})


def test_compound_order_mtm(simple_compound_order):
    order = simple_compound_order
    order.update_ltp({"aapl": 900, "goog": 300})
    assert order.mtm == {"aapl": 275, "goog": 380}
    order.update_ltp({"aapl": 885, "goog": 350})
    assert order.mtm == {"aapl": 110, "goog": -120}


def test_compound_order_total_mtm(simple_compound_order):
    order = simple_compound_order
    order.update_ltp({"aapl": 900, "goog": 300})
    assert order.total_mtm == 655
    order.update_ltp({"aapl": 885, "goog": 350})
    assert order.total_mtm == -10


def test_simple_order_execute():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(broker=broker)
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
        )
        assert broker.order_place.call_args_list[0] == call(**kwargs)


def test_simple_order_execute_kwargs():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(broker=broker, exchange="NSE", variety="regular")
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
            exchange="NSE",
            variety="regular",
        )
        assert broker.order_place.call_args_list[0] == call(**kwargs)


def test_simple_order_execute_do_not_update_existing_kwargs():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(
            broker=broker,
            exchange="NSE",
            variety="regular",
            quantity=20,
            order_type="MARKET",
        )
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
            exchange="NSE",
            variety="regular",
        )


def test_simple_order_modify():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
        )
        order.price = 630
        order.modify(broker=broker)
        broker.order_modify.assert_called_once()
        kwargs = dict(
            order_id="abcdef",
            quantity=10,
            order_type="LIMIT",
            price=630,
            trigger_price=0.0,
            disclosed_quantity=0,
        )
        assert broker.order_modify.call_args_list[0] == call(**kwargs)


def test_simple_order_cancel():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
        )
        order.cancel(broker=broker)
        broker.order_cancel.assert_called_once()
        kwargs = dict(order_id="abcdef")
        print(call(**kwargs))
        assert broker.order_cancel.call_args_list[0] == call(**kwargs)


def test_simple_order_do_not_execute_more_than_once():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        broker.order_place.return_value = "aaabbb"
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        for i in range(10):
            order.execute(broker=broker, exchange="NSE", variety="regular")
        broker.order_place.assert_called_once()


def test_simple_order_do_not_execute_completed_order():
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            filled_quantity=10,
        )
        for i in range(10):
            order.execute(broker=broker, exchange="NSE", variety="regular")
        broker.order_place.call_count == 0


def test_stop_order(stop_order):
    assert stop_order.count == 2
    assert stop_order.orders[0].order_type == "LIMIT"
    order = Order(
        symbol="aapl",
        side="sell",
        quantity=100,
        trigger_price=850,
        price=0,
        order_type="SL-M",
    )
    # Copy over from existing order as these are system attributes
    order.internal_id = stop_order.orders[-1].internal_id
    order.timestamp = stop_order.orders[-1].timestamp
    assert stop_order.orders[-1] == order


def test_stop_order_execute_all(stop_order):
    broker = stop_order.broker
    stop_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    stop_order.execute_all()
    assert broker.order_place.call_count == 2
    assert stop_order.orders[0].order_id == "aaaaaa"
    assert stop_order.orders[1].order_id == "bbbbbb"
    for i in range(10):
        stop_order.execute_all()
    assert broker.order_place.call_count == 2


def test_bracket_order_is_target_hit(bracket_order):
    broker = bracket_order.broker
    bracket_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    bracket_order.execute_all()
    assert broker.order_place.call_count == 2
    bracket_order.update_orders(
        {"aaaaaa": {"average_price": 930, "filled_quantity": 100, "status": "COMPLETE"}}
    )
    bracket_order.update_ltp({"aapl": 944})
    assert bracket_order.is_target_hit is False
    bracket_order.update_ltp({"aapl": 961})
    assert bracket_order.is_target_hit is True
    assert bracket_order.total_mtm == 3100


def test_bracket_order_do_target(bracket_order):
    broker = bracket_order.broker
    bracket_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    bracket_order.execute_all()
    bracket_order.update_orders(
        {"aaaaaa": {"average_price": 930, "filled_quantity": 100, "status": "COMPLETE"}}
    )
    for i in (944, 952, 960, 961):
        bracket_order.update_ltp({"aapl": i})
        bracket_order.do_target()
    broker.order_modify.assert_called_once()
    # TO DO: Add kwargs to check


def test_option_strategy_add_order(simple_compound_order):
    order = simple_compound_order
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        strategy = OptionStrategy(broker=broker)
        strategy.add_order(order)
        assert strategy._orders[0].broker == broker


def test_option_strategy_orders(simple_compound_order):
    order = simple_compound_order
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(order)
    assert len(strategy.orders) == 1
    strategy.add_order(order)
    assert len(strategy.orders) == 2


def test_option_strategy_all_orders(simple_compound_order):
    order = simple_compound_order
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    for i in range(3):
        strategy.add_order(order)
    assert len(strategy.all_orders) == 9


def test_option_strategy_update_ltp(simple_compound_order):
    order = simple_compound_order
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    for i in range(3):
        strategy.add_order(order)
    strategy.update_ltp({"goog": 415})
    for order in strategy.orders:
        order.ltp["goog"] == 415


def test_option_strategy_call(simple_compound_order, compound_order_average_prices):
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(simple_compound_order)
    strategy.add_order(compound_order_average_prices)
    assert strategy._call("count") == [3, 4]
    for i in range(2):
        strategy.add_order(simple_compound_order)
    assert strategy._call("count") == [3, 4, 3, 3]


def test_option_strategy_call_attribute_do_not_exist(
    simple_compound_order, compound_order_average_prices
):
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(simple_compound_order)
    strategy.add_order(compound_order_average_prices)
    assert strategy._call("no_attribute") == [None, None]


def test_option_strategy_update_ltp(
    simple_compound_order, compound_order_average_prices
):
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(simple_compound_order)
    strategy.add_order(compound_order_average_prices)
    strategy.update_ltp({"amzn": 300, "goog": 350})
    for order in strategy.orders:
        assert order.ltp == {"amzn": 300, "goog": 350}


def test_option_strategy_update_orders(
    simple_compound_order, compound_order_average_prices
):
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(simple_compound_order)
    strategy.add_order(compound_order_average_prices)
    # Reset order_id to None to simulate new orders
    for order in simple_compound_order.orders:
        order.order_id = None
    for order in compound_order_average_prices.orders:
        order.order_id = None
    order_data = {
        "aaaaaa": {"order_id": "aaaaaa", "exchange_order_id": 10001},
        "bbbbbb": {"order_id": "bbbbbb", "exchange_order_id": 10002},
        "333333": {"order_id": "333333", "exchange_order_id": 10003},
        "111111": {"order_id": "111111", "exchange_order_id": 10004},
    }
    strategy.update_orders(data=order_data)
    # Order not updated for completed orders
    for order in strategy.all_orders:
        if order.order_id in ["333333", "111111"]:
            assert (
                order.exchange_order_id
                == order_data[order.order_id]["exchange_order_id"]
            )
        else:
            # Already completed orders will have no exchange_order_id in dummy data
            assert order.exchange_order_id is None


def test_option_strategy_execute_all(
    simple_compound_order, compound_order_average_prices
):
    # Reset order_id to None to simulate new orders
    for order in simple_compound_order.orders:
        order.order_id = None
    for order in compound_order_average_prices.orders:
        order.order_id = None
        order.filled_quantity = 0
    with patch("fastbt.brokers.zerodha.Zerodha") as broker:
        strategy = OptionStrategy(broker=broker)
        strategy.add_order(simple_compound_order)
        strategy.add_order(compound_order_average_prices)
        strategy.add_order(deepcopy(compound_order_average_prices))
        strategy.execute_all()
        assert broker.order_place.call_count == 9
        strategy.execute_all()
        assert broker.order_place.call_count == 9
        #TO DO: Add more cases instead of replacing values

def test_option_strategy_total_mtm(compound_order_average_prices):
    broker = Broker()
    strategy = OptionStrategy(broker=broker)
    for i in range(5):
        strategy.add_order(compound_order_average_prices)
    strategy.update_ltp({"aapl": 900, "goog": 300})
    assert strategy.total_mtm == 52500
    for i in range(5):
        strategy.add_order(compound_order_average_prices)
    strategy.update_ltp({"aapl": 950, "goog": 550})
    assert strategy.total_mtm == 37500


def test_option_strategy_positions(simple_compound_order):
    broker = Broker()
    order = simple_compound_order
    strategy = OptionStrategy(broker=broker)
    strategy.add_order(deepcopy(order))
    strategy.add_order(deepcopy(order))
    order.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        filled_quantity=20,
        average_price=920,
        status="COMPLETE",
    )
    strategy.add_order(deepcopy(order))
    assert strategy.positions == {'aapl': 53, 'goog':-30}

def test_order_expires():
    known = pendulum.datetime(2021,1,1,12,tz='UTC')
    with pendulum.test(known):
        order = Order(symbol="aapl", side="buy", quantity=10)
        assert order.expires_in == (60*60*12)-1
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=600)
    assert order.expires_in == 600
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=-600)
    assert order.expires_in == 600
    
def test_order_expiry_times():
    known = pendulum.datetime(2021,1,1,9,30,tz='UTC')
    pendulum.set_test_now(known)
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=60)
    assert order.expires_in == 60
    assert order.time_to_expiry == 60
    assert order.time_after_expiry == 0
    known = known.add(seconds=40)
    pendulum.set_test_now(known)
    assert order.time_to_expiry == 20
    assert order.time_after_expiry == 0
    known = known.add(seconds=60)
    pendulum.set_test_now(known)
    assert order.time_to_expiry == 0
    assert order.time_after_expiry == 40
    pendulum.set_test_now()
