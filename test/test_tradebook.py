import unittest
import pandas as pd
import sys
sys.path.append('../')
from tradebook import TradeBook

trade = {
	'symbol': 'AAPL',
	'qty': 10,
	'price': 150,
	'order_type': 'B',
	'timestamp': '2018-01-01'
}

class TestTradeBook(unittest.TestCase):
	def setUp(self):
		self.tb = TradeBook(name='MyTradeBook')

	def test_add_trade(self):
		self.tb.add_trade(**trade)
		self.assertEqual(self.tb._trades[0]['id'], 1)
		self.assertEqual(self.tb._trades[0]['symbol'], 'AAPL')
		self.assertEqual(self.tb._trades[0]['qty'], 10)
		self.assertEqual(self.tb._trades[0]['price'], 150)
		self.assertEqual(self.tb._trades[0]['order_type'], 'B')
		self.assertEqual(self.tb._trades[0]['timestamp'], '2018-01-01')

	def test_add_trades(self):
		trades_array = []
		Trade = trade.copy()
		trades_array.append(Trade)

		Trade = trade.copy()
		Trade.update({'qty': 15, 'price': 145})
		trades_array.append(Trade)

		Trade = trade.copy()
		Trade.update({'qty': 25, 'order_type': 'S', 'price': 162, 'timestamp': '2018-01-10'})
		trades_array.append(Trade)
		self.tb.add_trades(trades_array)
		self.assertEqual(self.tb.trades[2]['id'], 3)
		self.assertEqual(self.tb.trades[2]['qty'], -25)
		self.assertEqual(self.tb.trades[2]['timestamp'], '2018-01-10')
		self.assertEqual(self.tb.get_trade_count(), 3)

	def test_count_trades(self):
		[self.tb.add_trade(**trade) for i in range(1000)]
		self.assertEqual(self.tb.get_trade_count(), 1000)


if __name__ == '__main__':
    unittest.main()
