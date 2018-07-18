import unittest
import pandas as pd
import sys
sys.path.append('../')
from intraday import TradingSystem
from functools import partial

def simple_strategy(x, plus=0.0, order_type='S'):
    # plus is an addition to calculate price
    x = x.copy() 
    x['price'] = (x['open'] * (1+plus)).apply(lambda x: round(x/0.01)*0.01)
    x['order_type'] = order_type
    return x[['symbol', 'price', 'order_type']]

class TestInitialize(unittest.TestCase):
    """
    Test whether initialize, getter and setters works properly
    """

    def setUp(self):
        self.ts = TradingSystem(capital=100000, universe=['ONE', 'TWO'],
        slippage=0.005, commission=0.001)

    def test_initialize_variables(self):
        self.assertEqual(self.ts.capital, 100000)
        self.assertEqual(self.ts.universe, ['ONE', 'TWO'])
        self.assertEqual(self.ts.slippage, 0.005)
        self.assertEqual(self.ts.commission, 0.001)

    def test_setters_variables(self):
        self.ts.capital = 200000
        self.ts.universe = ['THREE', 'FOUR']
        self.ts.slippage = 0.02
        self.ts.commission = 0.005
        self.assertEqual(self.ts.capital, 200000)
        self.assertEqual(self.ts.universe, ['THREE', 'FOUR'])
        self.assertEqual(self.ts.slippage, 0.02)
        self.assertEqual(self.ts.commission, 0.005)

class TestOrderPlace(unittest.TestCase):

    def setUp(self):
        df = pd.read_csv('sample.csv', index_col='timestamp',
        parse_dates=True)        
        self.ts = TradingSystem(capital=100000, data=df)
        self.ts.strategy = simple_strategy

    def test_data(self):
        self.assertEqual(self.ts.data.iloc[1].at['open'], 10.12)
        self.assertEqual(self.ts.data.iloc[-1].at['volume'], 333149)

    def test_trade_count(self):
        data = self.ts.data.sort_index()
        self.ts.run_backtest(start='2018-01-01', end='2018-01-01',
                            data=data)
        self.assertEqual(self.ts.tradebook.get_trade_count(), 12)                   
        self.ts.run_backtest(start='2018-01-01', end='2018-01-02',
                            data=data)        
        self.assertEqual(self.ts.tradebook.get_trade_count(), 24)
        self.ts.run_backtest(start='2018-01-01', end='2018-01-06')
        self.assertEqual(self.ts.tradebook.get_trade_count(), 72)

    def test_trade_qty(self):
        data = self.ts.data.sort_index()
        self.ts.run_backtest(start='2018-01-01', end='2018-01-02',data=data)
        tradebook = self.ts.tradebook.get_trades()
        tradebook.set_index(['timestamp', 'symbol', 'order_type'], inplace=True)
        idx = pd.IndexSlice
        self.assertEqual(tradebook.at[idx['2018-01-01', 'one', 'B'], 'qty'], 1666)
        self.assertEqual(tradebook.at[idx['2018-01-02', 'six', 'S'], 'qty'], -241)

        self.ts.run_backtest(start='2018-01-01', end='2018-01-06',
                             capital=200000, data=data)
        tradebook = self.ts.tradebook.get_trades()
        tradebook.set_index(['timestamp', 'symbol', 'order_type'], inplace=True)
        idx = pd.IndexSlice
        self.assertEqual(tradebook.at[idx['2018-01-01', 'two', 'B'], 'qty'], 33)
        self.assertEqual(tradebook.at[idx['2018-01-06', 'four', 'S'], 'qty'], -191)

    def test_price(self):
        from functools import partial
        partial_one = partial(simple_strategy, plus=0.01)
        partial_two = partial(simple_strategy, plus=-0.02, order_type='B')
        data = self.ts.data.sort_index()
        
        self.ts.strategy = partial_one        
        self.ts.run_backtest(start='2018-01-01', end='2018-01-02',data=data)
        tradebook = self.ts.tradebook.get_trades()
        tradebook.set_index(['timestamp', 'symbol', 'order_type'], inplace=True)
        idx = pd.IndexSlice
        self.assertEqual(tradebook.at[idx['2018-01-01', 'five', 'S'], 'price'], 25.25)
        self.assertEqual(tradebook.at[idx['2018-01-02', 'one', 'B'], 'price'], 10.22)
        self.assertEqual(tradebook.at[idx['2018-01-02', 'one', 'S'], 'price'], 10.22)
        self.assertEqual(tradebook.at[idx['2018-01-01', 'one', 'B'], 'qty'], 1650)

        self.ts.strategy = partial_two
        self.ts.run_backtest(start='2018-01-01', end='2018-01-02',data=data)
        tradebook = self.ts.tradebook.get_trades()
        tradebook.set_index(['timestamp', 'symbol', 'order_type'], inplace=True)
        idx = pd.IndexSlice
        self.assertEqual(tradebook.at[idx['2018-01-02', 'six', 'S'], 'price'], 66.5)
        self.assertEqual(tradebook.at[idx['2018-01-02', 'six', 'B'], 'price'], 67.62)
        self.assertEqual(tradebook.at[idx['2018-01-01', 'three', 'B'], 'price'], 98)
        self.assertEqual(tradebook.at[idx['2018-01-01', 'three', 'S'], 'price'], 101.2)
        self.assertEqual(tradebook.at[idx['2018-01-01', 'three', 'S'], 'qty'], -170)

    def test_backtest_with_default_parameters(self):
        pass                  
    

class TestFunctions(unittest.TestCase):

    def setUp(self):
        from fastbt.strategy import TradingSystem
        self.ts = TradingSystem(capital=100000)

    def test_universe_load_excel(self):
        pass

    def test_universe_load_excel_exception_no_sheet(self):
        pass

    def test_error_if_not_B_S(self):
        dct = {
            'timestamp': 'timestamp',
            'symbol': 'symbol',
            'price': 100,
            'order_type': 'BUY',
            'qty': 5,
            'open': 100, 'high':101, 'low': 99, 'close': 100
            }
        with self.assertRaises(ValueError):
            self.ts.validate_order(**dct)

    def test_error_if_stop_loss_negative(self):
        pass

    def test_error_if_target_negative(self):
        pass

    def test_error_both_target_and_stop_loss(self):
        pass

    def test_lamdba_function(self):
        pass

    def test_stop_loss_buy_generate_orders(self):
        pass


if __name__ == '__main__':
    unittest.main()
