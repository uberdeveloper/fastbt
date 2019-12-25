import pandas as pd
from fastbt.Meta import Broker

from fyers_api import accessToken, fyersModel
from functools import partial

class Fyers(Broker):
	"""
	Automated Trading class
	"""
	def __init__(self):
		"""
		To be implemented
		"""
		super(Fyers, self).__init__

	def authenticate(self):
		"""
		Fyers authentication to be implemented
		"""
		self.fyers = fyersModel.FyersModel()
		self._shortcuts()

	def _shortcuts(self):
		self.profile = partial(self.fyers.get_profile, token=self._token)
		self.holdings = partial(self.fyers.holdings, token=self._token)
		self.orders = partial(self.fyers.orders, token=self._token)
		self.trades = partial(self.fyers.tradebook, token=self._token)
		self.positions = partial(self.fyers.positions, token=self._token)





