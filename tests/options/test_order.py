import pytest
from fastbt.options.order import *
import pendulum

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
