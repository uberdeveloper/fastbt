import unittest
import pandas as pd
import sys
from sqlalchemy import create_engine
import pytest
from functools import partial
from random import randint
import yaml
import os
import context

from fastbt.rapid import *
R = lambda x: round(x, 2)

def compare(frame1, frame2):
    """
    Compare a random value from 2 dataframes
    return
        True if values are equal else False
    """
    r1 = randint(0, len(frame1)-1)
    r2 = randint(0, len(frame1.columns) - 1)
    return frame1.iloc[r1, r2] == frame2.iloc[r1, r2]


class TestRapidFetchData(unittest.TestCase):

    def setUp(self):
        self.con = create_engine('sqlite:///tests/data/data.sqlite3')
        self.tbl = 'eod'

    def test_fetch_data(self):
        """
        Additional date to be included for correct results due to
        """
        universe = ['one', 'two']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-02 00:00:00.000000'
        data = fetch_data(universe, start, end, self.con, self.tbl)
        self.assertEqual(data.shape[0], 4)

        universe = ['one', 'two', 'six']
        data = fetch_data(universe, start, end, self.con, self.tbl)
        self.assertEqual(data.shape[0], 6)

        end = '2018-01-06 00:00:00.000000'
        universe.append('five')
        data = fetch_data(universe, start, end, self.con, self.tbl)
        self.assertEqual(data.shape[0], 24)

    def test_fetch_data_condition(self):
        universe = ['one', 'two', 'three', 'four', 'five', 'six']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-06 00:00:00.000000'
        condition = ['open > 100']
        data = fetch_data(universe, start, end, self.con, self.tbl,
                where_clause = condition)       
        self.assertEqual(data.shape[0], 17)
        condition.append('volume > 200000')
        data = fetch_data(universe, start, end, self.con, self.tbl,
                where_clause = condition)       
        self.assertEqual(data.shape[0], 12)

class TestRapidPrepareData(unittest.TestCase):

    #TO DO: return in case of Empty dataframe
    def setUp(self):
        from sqlalchemy import create_engine
        con = create_engine('sqlite:///tests/data/data.sqlite3')
        tbl = 'eod'
        universe = ['one', 'two', 'three', 'four', 'five', 'six']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-06 00:00:00.000000'
        self.data = fetch_data(universe, start, end, con, tbl)

    def test_prepare_data(self):
        self.assertEqual(self.data.shape[0], 36)
        self.assertEqual(self.data.shape[1], 8)

        columns = [
            {'F': {'formula': '(open+close)/2', 'col_name': 'avgprice'}},
            {'I': {'indicator': 'SMA', 'period': 3, 'lag': 1, 'col_name': 'SMA3'}}
        ]
        conditions = [
            {'F': {'formula': 'open > prevclose', 'col_name': 'sig1'}},
            {'F': {'formula': 'open < sma3', 'col_name': 'sig2'}}
        ]
        data = prepare_data(self.data, columns)
        self.assertEqual(data.shape[1], 10)
        data = prepare_data(data, conditions)
        self.assertEqual(data.shape[1], 12)
        self.assertEqual(data.query('sig1==1').shape[0], 20)
        self.assertEqual(data.query('sig2==1').shape[0], 5) 

class TestRapidApplyPrices(unittest.TestCase):

    def setUp(self):
        from sqlalchemy import create_engine
        con = create_engine('sqlite:///tests/data/data.sqlite3')
        tbl = 'eod'
        universe = ['one', 'two', 'three', 'four', 'five', 'six']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-06 00:00:00.000000'
        self.data = fetch_data(universe, start, end, con, tbl)

    def test_apply_price_buy(self):
        # Simple default parameters
        idx = pd.IndexSlice
        R = lambda x: round(x, 2)
        conditions = ['open > prevclose']
        df = apply_prices(self.data, conditions, 'open', 3, 'B')
        self.assertEqual(df.shape[0], 20)
        df.set_index(['timestamp', 'symbol'], inplace=True)
        self.assertEqual(df.at[idx['2018-01-06', 'one'], 'price'], 10.65)
        self.assertEqual(df.query('low <= stop_loss').shape[0], 7)
        self.assertEqual(df.query('low <= stop_loss').price.sum(), 562.45)
        self.assertEqual(df.at[idx['2018-01-05', 'four'], 'sell'], 169.25)
        self.assertEqual(df.at[idx['2018-01-05', 'six'], 'sell'], 63.45)
        self.assertEqual(R(df.at[idx['2018-01-05', 'five'], 'stop_loss']), 25.70)
        self.assertEqual(df.at[idx['2018-01-05', 'five'], 'sell'], 27.4)

    def test_apply_price_sell(self):
        idx = pd.IndexSlice
        R = lambda x: round(x, 2)
        conditions = ['open > prevclose']
        df = apply_prices(self.data, conditions, 'open', 3, 'S')
        df.set_index(['timestamp', 'symbol'], inplace=True)
        self.assertEqual(df.query('stop_loss >= high').shape[0], 13)
        self.assertEqual(R(df.at[idx['2018-01-02', 'three'], 'stop_loss']), 105.05)
        self.assertEqual(df.at[idx['2018-01-05', 'four'], 'price'], 174.5)
        self.assertEqual(df.at[idx['2018-01-03', 'three'], 'buy'], 110) 

    def test_order_raise_error(self):
        pass

class TestRapidRunStrategy(unittest.TestCase):

    def setUp(self):
        from sqlalchemy import create_engine
        con = create_engine('sqlite:///tests/data/data.sqlite3')
        tbl = 'eod'
        universe = ['one', 'two', 'three', 'four', 'five', 'six']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-06 00:00:00.000000'
        data = fetch_data(universe, start, end, con, tbl)
        conditions = ['open > prevclose']
        self.data = apply_prices(data, conditions, 'open', 3, 'B')

    def test_run_strategy_default(self):
        idx = pd.IndexSlice
        df = run_strategy(self.data, 'price', True, 5)
        df = df.set_index(['timestamp', 'symbol']).sort_index()
        print('IDX', df.loc[idx['2018-01-03', 'four'], 'stop_loss'])
        self.assertEqual(R(df.at[idx['2018-01-03', 'four'], 'stop_loss']), 162.95)
        self.assertEqual(R(df.at[idx['2018-01-05', 'five'], 'price']), 26.5)


    def test_run_strategy_custom(self):
        def func(x):
            return x.iloc[[0]]
        df = run_strategy(self.data, 'price', True, 5, func)
        self.assertEqual(len(df), 6)

class TestRapidGetOutput(unittest.TestCase):

    def setUp(self):
        from sqlalchemy import create_engine
        con = create_engine('sqlite:///tests/data/data.sqlite3')
        tbl = 'eod'
        universe = ['one', 'two', 'three', 'four', 'five', 'six']
        start, end = '2018-01-01 00:00:00.000000', '2018-01-06 00:00:00.000000'
        data = fetch_data(universe, start, end, con, tbl)
        conditions = ['open > prevclose']
        data = apply_prices(data, conditions, 'open', 3, 'B')
        self.data = run_strategy(data, 'price', True, 5)

    def test_get_output_default(self):
        result = get_output(self.data, 100000, 1, 0,0)
        self.assertEqual(R(result.profit.sum()), -715.09)
        self.assertEqual(result.qty.sum(), 26506)
        by_day = result.groupby('timestamp').profit.sum()
        self.assertEqual(R(by_day.loc['2018-01-04']), -3153.15)

def test_backtest_data():
    import yaml
    with open('tests/data/backtest.yaml') as f:
        kwargs = yaml.load(f)
    kwargs['connection'] = create_engine('sqlite:///tests/data/data.sqlite3')
    kwargs['tablename'] = 'eod'
    result_one = backtest(**kwargs)

    data = pd.read_csv('tests/data/sample.csv', parse_dates=['timestamp'])
    del kwargs['connection']
    del kwargs['tablename']
    kwargs['data'] = data
    result_two = backtest(**kwargs)
    assert metrics(result_one, 100000) == metrics(result_two, 100000)
    assert result_one.shape == result_two.shape
    from random import randint
    for i in range(10):
        assert compare(result_one, result_two)

def test_stop_loss_zero():
    pass

def _build_input_output():
    """
    This function builds the input and output
    from results for passing to pytest
    """
    data = pd.read_csv('tests/data/results.csv').to_dict(orient='records')
    with open('tests/data/BT.yaml') as f:
        params = yaml.load(f)

    input_map = {
    'start': 'start',
    'end': 'end',
    'capital': 'capital',
    'lev': 'leverage',
    'comm': 'commission',
    'slip': 'slippage',
    'sl': 'stop_loss',
    'order': 'order',
    'limit': 'limit',
    'universe': 'universe',
    'sort_by': 'sort_by',
    'sort_mode': 'sort_mode'
    }
    output_cols = ['profit', 'commission', 'slippage', 'net_profit',
                    'high', 'low', 'drawdown', 'returns', 'sharpe']
    final = []
    for d in data:
        kwargs = {}
        for k,v in input_map.items():
            kwargs[v] = d[k]
        if kwargs.get('universe') != 'all':
            kwargs['universe'] = kwargs['universe'].split(',')
        kwargs['start'] = pd.to_datetime(kwargs['start'])
        kwargs['end'] = pd.to_datetime(kwargs['end'])
        kwargs.update(params.get(d['strategy']))
        result = {}
        for col in output_cols:
            result[col] = d[col]
        final.append((kwargs, result))
    return final

con = create_engine('sqlite:///tests/data/data.sqlite3')
tbl = 'eod'
bt = partial(backtest, connection=con, tablename=tbl)
@pytest.mark.parametrize("kwargs, expected", _build_input_output())
def test_backtest_results(kwargs, expected):    
    result = metrics(bt(**kwargs), kwargs['capital'])
    for k,v in result.items():
        assert pytest.approx(v, rel=0.001, abs=0.001) == expected[k]

def test_empty_dataframe_result():
    params = {
        'start': '2020-01-01',
        'end': '2020-01-05',
        'sort_by': 'open'
    }
    with pytest.raises(ValueError):
        bt(**params)

    params.update({'start': '2017-01-01', 'conditions':['open > 20000']})
    with pytest.raises(ValueError):
        bt(**params)

def test_no_datasource():
    params = {
        'start': '2018-01-01',
        'end': '2020-01-05'
    }
    with pytest.raises(ValueError):
        backtest(**params)
  
    params.update({'tablename': tbl})
    with pytest.raises(ValueError):
        backtest(**params)   
    del params['tablename']

    params.update({'connection': con})
    with pytest.raises(ValueError):
        backtest(**params)

    params.update({'tablename': tbl})
    backtest(**params)

def test_no_columns():
    params = {
        'start': '2018-01-01',
        'end': '2018-01-07',
        'sort_by': 'open',
        'conditions': ['open > 0'],
        'limit': 10
    }
    assert len(bt(**params)) == 36

def test_no_conditions():
    params = {
        'start': '2018-01-01',
        'end': '2018-01-07',
        'sort_by': 'open',
        'columns': [{'F': {'formula': '(open+close)/2', 'col_name': 'avgprice'}}],
        'limit': 10
    }
    assert len(bt(**params)) == 36

def test_no_columns_no_conditions():
    params = {
        'start': '2018-01-01',
        'end': '2018-01-07',
        'sort_by': 'open',
        'limit': 10
        }
    df1 = pd.read_csv('tests/data/sample.csv', parse_dates=['timestamp'])
    df1 = df1.sort_values(by=['timestamp', 'symbol'])
    df2 = bt(**params).sort_values(by=['timestamp', 'symbol'])
    for i in range(20):
        assert compare(df1, df2)

def test_strategy_output():
    params = {
        'start': '2018-01-01',
        'end': '2018-01-07',
        'sort_by': 'price',
        'limit': 10
    }
    df1 = pd.read_csv('tests/data/sample.csv', parse_dates=['timestamp'])
    df1 = df1.sort_values(by=['timestamp', 'symbol'])
    strategy = lambda x: x
    output = lambda x:x
    df2 = bt(**params, strategy=strategy, output=output).sort_values(by=['timestamp', 'symbol'])
    for i in range(20):
        assert compare(df1, df2)

@pytest.mark.parametrize("stop_loss", [1,2,3])
@pytest.mark.parametrize("order", ['B', 'S'])
@pytest.mark.parametrize("limit", [3,5])
def test_same_results(stop_loss, order, limit):
    # test whether results are same for both backtest
    # function and when functions are run individually
    params = {
    'start': '2018-01-01',
    'end': '2018-01-10',
    'price': 'open * 0.999',
    'columns':[{'F': {'formula': '(open+close)/2', 'col_name': 'avgprice'}}],
    'conditions': ['open > 50'],
    'sort_by': 'price'
    }
    params.update({'stop_loss': stop_loss, 'order': order, 'limit': limit})
    result_one = bt(**params)
    df = fetch_data('all', '2018-01-01','2018-01-10', con, tbl) 
    df = prepare_data(df, params['columns'])
    df = apply_prices(df, params['conditions'], params['price'],
        stop_loss=stop_loss, order=order)
    df = run_strategy(df, params['sort_by'], True, limit=limit)
    result_two = get_output(df, 100000, 1)
    for i in range(50):
        assert compare(result_one, result_two)

def test_backtest_from_excel():
    my_result = {
        'profit': -715.09,
        'commission': 0.0,
        'slippage': 0.0,
        'net_profit': -715.09,
        'high': 1200.76,
        'low': -2599.34,
        'drawdown': -0.026,
        'returns': -0.007,
        'sharpe': -0.065
    }
    con = create_engine('sqlite:///tests/data/data.sqlite3')
    tbl = 'eod'
    result = backtest_from_excel('tests/data/backtest.xls', connection=con, tablename=tbl)
    result = metrics(result, 100000)
    for k,v in my_result.items():
        assert round(result[k], 3) == v

def test_backtest_from_json():
    my_result = {
        'profit': -715.09,
        'commission': 0.0,
        'slippage': 0.0,
        'net_profit': -715.09,
        'high': 1200.76,
        'low': -2599.34,
        'drawdown': -0.026,
        'returns': -0.007,
        'sharpe': -0.065
    }
    con = create_engine('sqlite:///tests/data/data.sqlite3')
    tbl = 'eod'
    result = backtest_from_json('tests/data/backtest.json', connection=con, tablename=tbl)
    result = metrics(result, 100000)
    for k,v in my_result.items():
        assert round(result[k], 3) == v

def test_backtest_from_yaml():
    my_result = {
        'profit': -715.09,
        'commission': 0.0,
        'slippage': 0.0,
        'net_profit': -715.09,
        'high': 1200.76,
        'low': -2599.34,
        'drawdown': -0.026,
        'returns': -0.007,
        'sharpe': -0.065
    }
    con = create_engine('sqlite:///tests/data/data.sqlite3')
    tbl = 'eod'
    result = backtest_from_yaml('tests/data/backtest.yaml', connection=con, tablename=tbl)
    result = metrics(result, 100000)
    for k,v in my_result.items():
        assert round(result[k], 3) == v
