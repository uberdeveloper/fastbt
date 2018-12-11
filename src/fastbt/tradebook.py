import pandas as pd
from collections import Counter

class TradeBook:
	def __init__(self, name='tradebook'):
		self._name = name
		self._trades = []
		self._positions = Counter()

	def __repr__(self):
		string = '{name} with {count} entries and {pos} positions'
		pos = sum([1 for x in self._positions.values() if x!= 0])
		string = string.format(
			name=self._name, count=len(self._trades), pos=pos)
		return string

	@property
	def name(self):
		return self._name

	@property
	def trades(self):
		return self._trades

	@property
	def positions(self):
		return self._positions

	def add_trade(self, timestamp, symbol, price, qty, order):
		"""
		Add a trade to the tradebook
		timestamp
			python/pandas timestamp
		symbol
			an unique identifier for the security
		price
			price of the security
		qty
			quantity of the security
		order
			B for B and S for SELL
		"""
		o = {'B': 1, 'S': -1}

		q = qty * o[order]
		dct = {
			'ts': timestamp,
			'symbol': symbol,
			'price': price,
			'qty': q,
			'order': order
		}
		self._trades.append(dct)
		self._positions.update({symbol:q})



