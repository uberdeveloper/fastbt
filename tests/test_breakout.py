import pytest
import pendulum
import random
from fastbt.models.breakout import Breakout, StockData

@pytest.fixture
def base_breakout():
    return Breakout(symbols=['GOOG','AAPL'],
             instrument_map={'GOOG':1010,'AAPL':2100})
    

def test_breakout_parent_defaults(base_breakout):
    ts = base_breakout
    assert ts.SYSTEM_START_TIME == pendulum.today(tz='Asia/Kolkata').add(hours=9,minutes=15)
    assert ts.SYSTEM_END_TIME == pendulum.today(tz='Asia/Kolkata').add(hours=15,minutes=15)
    assert ts.env == 'paper'
    assert ts.done is False


def test_stock_data(base_breakout):
    ts = base_breakout
    assert len(ts.data) == 2
    my_data = { 
            'GOOG': StockData(name='GOOG', token=1010),
            'AAPL': StockData(name='AAPL', token=2100)
            }
    assert ts.data == my_data


def test_rev_map(base_breakout):
    ts = base_breakout
    assert ts._rev_map == {1010: 'GOOG', 2100: 'AAPL'} 







