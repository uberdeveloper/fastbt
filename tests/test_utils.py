import pandas as pd
import numpy as np
import pytest
import unittest
import sys
import context

from fastbt.utils import *

def equation(a,b,c,x,y):
    return a*x**2 + b*y + c

def test_multiargs_simple():
    seq = pd.Series([equation(1,2,3,4,y) for y in range(20, 30)]).sort_index()
    seq.index = range(20,30)
    constants = {'a':1, 'b':2, 'c':3, 'x':4}
    variables = {'y': range(20, 30)}
    par = multi_args(equation, constants=constants, variables=variables).sort_index()
    # Check both values and indexes
    for x,y in zip(seq, par):
        assert x == y
    for x,y in zip (seq.index, par.index):
        assert (x,) == y

def test_multiargs_product():
    seq = []
    for x in range(0,10):
        for y in range(10,15):
            seq.append(equation(1,2,3,x,y))
    index = pd.MultiIndex.from_product([range(0, 10), range(10, 15)])
    seq = pd.Series(seq)
    seq.index = index
    seq = seq.sort_index()
    constants =  {'a':1, 'b':2, 'c':3}
    variables = {'x': range(0, 10), 'y': range(10,15)}
    par = multi_args(equation, constants=constants, 
        variables=variables, isProduct=True).sort_index()
    # Check both values and indexes
    for x,y in zip(seq, par):
        assert x == y
    for x,y in zip (seq.index, par.index):
        assert x == y   

def test_multiargs_max_limit():
    seq = []
    for x in range(0,100):
        for y in range(100, 150):
            seq.append(equation(1,2,3,x,y))
    index = pd.MultiIndex.from_product([range(0, 100), range(100, 150)])
    seq = pd.Series(seq)
    seq.index = index
    seq = seq.sort_index()
    constants =  {'a':1, 'b':2, 'c':3}
    variables = {'x': range(0, 100), 'y': range(100,150)}
    par = multi_args(equation, constants=constants, 
        variables=variables, isProduct=True).sort_index()
    assert len(par) == 1000
    assert len(seq) == 5000
    # Check both values and indexes
    for x,y in zip(seq, par):
        assert x == y
    for x,y in zip (seq.index, par.index):
        assert x == y

@pytest.mark.parametrize("maxLimit", [2000, 3000, 5000, 10000])
def test_multiargs_max_limit_adjust(maxLimit):
    seq = []
    for x in range(0,100):
        for y in range(100, 150):
            seq.append(equation(1,2,3,x,y))
    index = pd.MultiIndex.from_product([range(0, 100), range(100, 150)])
    seq = pd.Series(seq)
    seq.index = index
    seq = seq.sort_index()
    constants =  {'a':1, 'b':2, 'c':3}
    variables = {'x': range(0, 100), 'y': range(100,150)}
    par = multi_args(equation, constants=constants, 
        variables=variables, isProduct=True, maxLimit=maxLimit).sort_index()
    assert len(par) == min(maxLimit, 5000)
    assert len(seq) == 5000
    # Check both values and indexes
    for x,y in zip(seq, par):
        assert x == y
    for x,y in zip (seq.index, par.index):
        assert x == y

def test_tick():
    assert tick(112.71) == 112.7
    assert tick(112.73) == 112.75
    assert tick(1054.85, tick_size=0.1) == 1054.8
    assert tick(1054.851, tick_size=0.1) == 1054.9
    assert tick(104.73, 1) == 105
    assert tick(103.2856, 0.01) == 103.29
    assert tick(0.007814, 0.001) == 0.008
    assert tick(0.00003562, 0.000001) == 0.000036
    assert tick(0.000035617, 0.00000002) == 0.00003562

def test_tick_series():
    s = pd.Series([100.43, 200.32, 300.32])
    result = [100.45, 200.3, 300.3]
    for x,y in zip(tick(s), result):
        assert x==y

def test_stop_loss():
    assert stop_loss(100, 3) == 97
    assert stop_loss(100, 3, order='S') == 103
    assert stop_loss(1013, 2.5, order='B', tick_size=0.1) == 987.7
    assert stop_loss(100, -3) == 103 # This should be depreceated
    assert stop_loss(100, -3, order='S') == 97

def test_stop_loss_error():
    with pytest.raises(ValueError):
        assert stop_loss(100, 3, 'BS')

def test_stop_loss_series():
    p = pd.Series([100.75, 150.63, 180.32])
    result = [95.71, 143.1, 171.3]
    for x,y in zip(stop_loss(p, 5, tick_size=0.01), result):
        assert pytest.approx(x, rel=0.001, abs=0.001) == y

    # Test for sell
    result = [105.79, 158.16, 189.34]
    for x,y in zip(stop_loss(p, 5, order='S', tick_size=0.01), result):
        assert pytest.approx(x, rel=0.001, abs=0.001) == y

def test_create_orders_simple():
    df = pd.DataFrame(np.arange(20).reshape(5,4), columns=list('ABCD'))
    orders = create_orders(df, {'A': 'one', 'B': 'two', 'C': 'three', 'D': 'four'},
        exchange='NSE', num=range(5))
    df['exchange'] = 'NSE'
    df['num'] = [0,1,2,3,4]
    assert list(orders.columns) == ['one', 'two', 'three', 'four', 'exchange', 'num']
    assert list(df.exchange) == ['NSE'] * 5

class TestRecursiveMerge(unittest.TestCase):

    def setUp(self):
        df1 = pd.DataFrame(np.random.randn(6,3), columns=list('ABC'))
        df2 = pd.DataFrame(np.random.randn(10,3), columns=list('DEF'))
        df3 = pd.DataFrame(np.random.randn(7,4), columns=list('GHIJ'))
        df4 = pd.DataFrame(np.random.randn(10,7), columns=list('AMNDXYZ'))
        df1['idx'] = range(100,106)
        df2['idx'] = range(100, 110)
        df3['idx'] = range(100, 107)
        df4['idx'] = range(100, 110)
        self.dfs = [df1, df2, df3, df4]

    def test_recursive_merge_simple(self):
        df = recursive_merge(self.dfs)
        assert len(df) == 6
        assert df.shape == (6, 21)
        assert df.loc[3, 'X'] == self.dfs[3].loc[3, 'X']
        assert df.iloc[2, 11] == self.dfs[2].iloc[2, 3]

    def test_recursive_on(self):
        df = recursive_merge(self.dfs, on=['idx'])
        assert df.shape == (6, 18)
        assert df.loc[3, 'X'] == self.dfs[3].loc[3, 'X']
        assert df.iloc[2, 11] == self.dfs[3].iloc[2, 0]

    def test_recursive_on(self):
        dct = {'1': 'D', '2': 'G', '3': 'X'}
        df = recursive_merge(self.dfs, on=['idx'], columns=dct)
        assert df.shape == (6, 7)
        assert list(sorted(df.columns)) == ['A', 'B', 'C', 'D', 'G', 'X', 'idx']
        assert df.loc[3, 'X'] == self.dfs[3].loc[3, 'X']

def test_get_nearest_option():
    assert get_nearest_option(23120) == [23100]
    assert get_nearest_option(23120, opt='P') == [23100]
    assert get_nearest_option(28427, n=3) == [28400, 28500, 28600]
    assert get_nearest_option(28400, n=3) == [28400, 28500, 28600]
    assert get_nearest_option(28495, n=5, opt='P') == [28400, 28300, 28200, 28100, 28000]
    assert get_nearest_option(3000, n=3, step=30) == [3000, 3030, 3060]

def test_calendar_simple():
    s,e = '2019-01-01',  '2019-01-10'
    for a,b in zip(calendar(s,e), pd.bdate_range(s,e)):
        assert a == b
    for a,b in zip(calendar(s,e,alldays=True), pd.date_range(s,e)):
        assert a == b

def test_calendar_holidays():
    s,e,h = '2019-01-01',  '2019-01-07', ['2019-01-03', '2019-01-07']
    bdays = [pd.to_datetime(dt) for dt in [
        '2019-01-01', '2019-01-02', '2019-01-04'
    ]]
    for a,b in zip(calendar(s,e,h), bdays):
        assert a == b
    days = [pd.to_datetime(dt) for dt in [
        '2019-01-01', '2019-01-02', '2019-01-04', '2019-01-05', '2019-01-06'
    ]]
    for a,b in zip(calendar(s,e,h,True), days):
        assert a == b 

def test_calendar_bdate_timestamp():
    s,e,st,et = '2019-01-01',  '2019-01-01', '04:00', '18:00'
    for a,b in zip(calendar(s,e,start_time=st, end_time=et),
        pd.date_range('2019-01-01 04:00', '2019-01-01 18:00', freq='H')):
        assert a == b

def test_calendar_timestamp_length():
    s,e,st = '2019-01-01', '2019-01-01', '04:00'
    assert len(calendar(s,e,start_time=st, freq='1min')) == 1200
    assert len(calendar(s,e,start_time=st, freq='H')) == 20

    et = '16:00'
    assert len(calendar(s,e,end_time=et, freq='1min')) == 961
    assert len(calendar(s,e,end_time=et, freq='H')) == 17

    assert len(calendar(s,e,start_time=st, end_time=et, freq='1min')) == 721
    assert len(calendar(s,e,start_time=st, end_time=et, freq='H')) == 13

def test_calendar_timestamp_position():
    s,e,st,et = '2019-01-01', '2019-01-04', '10:00', '18:00'
    ts = calendar(s,e,start_time=st, end_time=et, freq='1min')
    assert str(ts[721]) == '2019-01-02 14:00:00'
    assert str(ts[1000]) == '2019-01-03 10:38:00'

def test_calendar_multiple_days():
    s,e,st,et = '2019-01-01', '2019-01-10', '10:00:00', '21:59:59'
    kwargs = {'start': s, 'end': e, 'start_time': st, 'end_time': et}
    holidays = ['2019-01-04', '2019-01-05', '2019-01-06']
    assert len(calendar(**kwargs)) == 8
    assert len(calendar(alldays=True, **kwargs)) == 10
    assert len(calendar(holidays=holidays, alldays=True, **kwargs)) == 7
    assert len(calendar(holidays=holidays, alldays=True, **kwargs, freq='H')) == 7*12
    assert len(calendar(holidays=holidays, alldays=True, **kwargs, freq='10min')) == 7*12*6
    assert len(calendar(holidays=holidays, alldays=True, **kwargs, freq='s')) == 7*12*3600











        
