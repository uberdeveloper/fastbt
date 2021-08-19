import pytest
from fastbt.options.order import *
from fastbt.Meta import Broker
from collections import Counter
import pendulum

@pytest.fixture
def simple_compound_order():
    com = CompoundOrder(broker=Broker())
    com.add_order(symbol='aapl', quantity=20, side='buy',
    filled_quantity=20, status='COMPLETE')
    com.add_order(symbol='goog', quantity=10, side='sell',
    filled_quantity=10, status='COMPLETE')
    com.add_order(symbol='aapl', quantity=12, side='sell',
    filled_quantity=9)
    return com

def test_order_simple():
    order = Order(symbol='aapl', side='buy', quantity=10)
    assert order.quantity == 10
    assert order.timestamp is not None
    assert order.internal_id is not None

def test_is_complete():
    order = Order(symbol='aapl', side='buy', quantity=10)
    assert order.is_complete is False
    order.filled_quantity = 10
    assert order.is_complete is True

def test_is_complete_other_cases():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.filled_quantity = 6
    assert order.is_complete is False
    order.cancelled_quantity = 4
    assert order.is_complete is True

def test_is_pending():
    order = Order(symbol='aapl', side='buy', quantity=10)
    assert order.is_pending is True
    order.filled_quantity = 10
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5,5
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5,4
    assert order.is_pending is True
    order.status = 'COMPLETE'
    assert order.is_pending is False


@pytest.mark.parametrize(
    "test_input,expected",[
        ((15134,), 15100),
        ((15134,0,50), 15150),
        ((15176,0,50), 15200),

    ]
)
def test_get_option(test_input, expected):
    print(test_input)
    assert get_option(*test_input) == expected


def test_update_order_simple():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.update({
        'filled_quantity': 7,
        'average_price': 912,
        'exchange_order_id': 'abcd'
    })
    assert order.filled_quantity == 7
    assert order.average_price == 912
    assert order.exchange_order_id == 'abcd'

def test_update_order_non_attribute():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.update({
        'filled_quantity': 7,
        'average_price': 912,
        'message': 'not in attributes'
    })
    assert order.filled_quantity == 7
    assert hasattr(order, 'message') is False

def test_update_order_do_not_update_when_complete():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.filled_quantity = 10
    order.update({'average_price': 912})
    assert order.average_price is None
    order.filled_quantity = 7
    order.update({'average_price': 912})
    assert order.average_price  == 912
    order.average_price = 0
    # This is wrong; this should never be updated directly
    order.status = 'COMPLETE'
    assert order.average_price == 0
    assert order.filled_quantity == 7

def test_compound_order_count(simple_compound_order):
    order = simple_compound_order
    assert order.count == 3

def test_compound_order_positions(simple_compound_order):
    order = simple_compound_order
    assert order.positions == Counter({'aapl':11, 'goog':-10})
    order.add_order(symbol='boe', side='buy',
    quantity=5, filled_quantity=5)
    assert order.positions == Counter({'aapl':11, 'goog':-10, 'boe':5})

def test_compound_order_add_order():
    order = CompoundOrder(broker=Broker())
    order.add_order(symbol='aapl', quantity=5, side='buy',
    filled_quantity=5)
    order.add_order(symbol='aapl', quantity=4, side='buy',
    filled_quantity=4)
    assert order.count == 2
    assert order.positions == Counter({'aapl': 9})


