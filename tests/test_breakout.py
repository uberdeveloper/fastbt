import pytest
import pendulum
import random
from fastbt.models.breakout import Breakout, StockData, HighLow
from pydantic import ValidationError

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
    assert ts.data['GOOG'].high is None
    assert ts.data['AAPL'].low is None


def test_rev_map(base_breakout):
    ts = base_breakout
    assert ts._rev_map == {1010: 'GOOG', 2100: 'AAPL'} 
    

def test_high_low(base_breakout):
    ts = base_breakout
    ts.update_high_low([
            HighLow(symbol='AAPL', high=150, low=120),
            HighLow(symbol='GOOG', high=150, low=120), 
            ])
    assert ts.data['AAPL'].high == 150
    assert ts.data['GOOG'].low == 120 

def test_high_low_dict(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'AAPL', 'high': 150, 'low':120}
        ])
    assert ts.data['AAPL'].high == 150
    
def test_high_low_dict_extra_values(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'AAPL', 'high': 150, 'low':120, 'open': 160}
        ])
    assert ts.data['AAPL'].high == 150
    
def test_high_low_dict_no_symbols(base_breakout):
    ts = base_breakout
    ts.update_high_low([
        {'symbol': 'DOW', 'high': 150, 'low':120, 'open': 160} ])
    assert ts.data['AAPL'].high is None
    assert ts.data['GOOG'].low is None

def test_high_low_no_data_raise_error(base_breakout):
    ts = base_breakout
    with pytest.raises(ValidationError):
        ts.update_high_low([
            {'symbol': 'AAPL', 'high':15}
            ])

    







