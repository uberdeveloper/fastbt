"""
This is the meta trading class from which other classes
are derived
"""
from fastbt.tradebook import TradeBook

class TradingSystem:
	def __init__(self, auth=None, tradebook=None):
		"""
		Initialize the system
		"""
		self.auth = auth
		self._cycle = 0
		self._data = []
		if tradebook is None:
			self.tb = TradeBook(name="TradingSystem")
		else:
			self.tb = tradebook
		# List of options for the system
		self._options = {
			'max_positions': 20
		}
		

	@property
	def options(self):
		return self._options

	@property
	def data(self):
		return self._data

	@property
	def cycle(self):
		return self._cycle

	def fetch(self):
		"""
		Data fetcher.
		Use this method to fetch data
		"""
		pass

	def process(self):
		"""
		preprocess data before storing it
		This method should update the data property
		for further processing
		"""
		pass

	def signal(self):
		"""
		Entry and exit conditions checking must go here
		"""
		pass

	def order(self):
		"""
		Order placement should go here and adjust tradebook
		"""
		pass

	def run(self):
		"""
		This should be the only method to call at 
		a high level
		Must update the cycle after run
		"""
		self.fetch-data()
		self.process()
		self.signal()
		self.order()
		self._cycle += 1