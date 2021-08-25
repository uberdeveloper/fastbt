import pytest
from fastbt.options.order import *
from fastbt.Meta import Broker
from collections import Counter
import pendulum

@pytest.fixture
def simple_compound_order():
    com = CompoundOrder(broker=Broker())
    com.add_order(symbol='aapl', quantity=20, side='buy',
    filled_quantity=20, average_price=920, status='COMPLETE', order_id='aaaaaa')
    com.add_order(symbol='goog', quantity=10, side='sell',
    filled_quantity=10, average_price=338, status='COMPLETE', order_id='bbbbbb')
    com.add_order(symbol='aapl', quantity=12, side='sell',
    filled_quantity=9, average_price=975, order_id='cccccc')
    return com

@pytest.fixture
def compound_order_average_prices():
    com = CompoundOrder(broker=Broker())
    com.add_order(symbol='aapl', quantity=20,side='buy',
    filled_quantity=20, average_price=1000)
    com.add_order(symbol='aapl', quantity=20,side='buy',
    filled_quantity=20, average_price=900)
    com.add_order(symbol='goog', quantity=20,side='sell',
    filled_quantity=20, average_price=700)
    com.add_order(symbol='goog', quantity=15,side='sell',
    filled_quantity=15, average_price=600)
    return com


def test_order_simple():
    order = Order(symbol='aapl', side='buy', quantity=10)
    assert order.quantity == 10
    assert order.pending_quantity == 10
    assert order.filled_quantity == 0
    assert order.timestamp is not None
    assert order.internal_id is not None

def test_order_is_complete():
    order = Order(symbol='aapl', side='buy', quantity=10)
    assert order.is_complete is False
    order.filled_quantity = 10
    assert order.is_complete is True

def test_order_is_complete_other_cases():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.filled_quantity = 6
    assert order.is_complete is False
    order.cancelled_quantity = 4
    assert order.is_complete is True

def test_order_is_pending():
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


def test_order_update_simple():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.update({
        'filled_quantity': 7,
        'average_price': 912,
        'exchange_order_id': 'abcd'
    })
    assert order.filled_quantity == 7
    assert order.average_price == 912
    assert order.exchange_order_id == 'abcd'

def test_order_update_non_attribute():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.update({
        'filled_quantity': 7,
        'average_price': 912,
        'message': 'not in attributes'
    })
    assert order.filled_quantity == 7
    assert hasattr(order, 'message') is False

def test_order_update_do_not_update_when_complete():
    order = Order(symbol='aapl', side='buy', quantity=10)
    order.filled_quantity = 10
    order.update({'average_price': 912})
    assert order.average_price == 0
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

def test_compound_order_average_buy_price(compound_order_average_prices):
    order = compound_order_average_prices
    assert order.average_buy_price == dict(aapl=950)

def test_compound_order_average_sell_price(compound_order_average_prices):
    order = compound_order_average_prices
    # Rounding to match significane
    dct = order.average_sell_price
    for k,v in dct.items():
        dct[k] = round(v,2)
    assert dct == dict(goog=657.14)

def test_compound_order_update_orders(simple_compound_order):
    order = simple_compound_order
    order_data = {
        'aaaaaa':{
            'order_id': 'aaaaaa',
            'exchange_order_id': 'hexstring',
            'price': 134,
            'average_price': 134
        },
        'cccccc':{
            'order_id': 'cccccc',
            'filled_quantity': 12,
            'status': 'COMPLETE',
            'average_price': 180

        }
    }
    updates = order.update_orders(order_data)
    assert updates == {'aaaaaa': False, 'bbbbbb': False, 'cccccc': True}
    assert order.orders[-1].filled_quantity ==  12
    assert order.orders[-1].status == 'COMPLETE'
    assert order.orders[-1].average_price == 180

def test_compound_order_buy_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.buy_quantity == {'aapl': 20}

def test_compound_order_sell_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.sell_quantity == {'goog':10, 'aapl': 9}

def test_compound_order_update_ltp(simple_compound_order):
    order = simple_compound_order
    assert order.ltp == {}
    assert order.update_ltp({'amzn':300, 'goog': 350}) == {'amzn': 300, 'goog': 350}
    order.update_ltp({'aapl': 600})
    assert order.ltp == {'amzn': 300, 'goog':350, 'aapl': 600}
    assert order.update_ltp({'goog':365}) ==  {'amzn': 300, 'goog':365, 'aapl': 600}

def test_compound_order_net_value(simple_compound_order, compound_order_average_prices):
    order = simple_compound_order
    order2 = compound_order_average_prices
    order._orders.extend(order2.orders)
    assert order.net_value == Counter({'aapl': 47625, 'goog': -26380})