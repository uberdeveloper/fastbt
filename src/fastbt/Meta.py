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
		self._pipeline = [
			getattr(self, 'fetch'),
			getattr(self, 'process'),
			getattr(self, 'signal'),
			getattr(self, 'order')
		]
		if tradebook is None:
			self.tb = TradeBook(name="TradingSystem")
		else:
			self.tb = tradebook
		# List of options for the system
		self._options = {
			'max_positions': 20,
			'cycle': 1e6
		}		

	@property
	def options(self):
		return self._options.copy()

	@property
	def data(self):
		return self._data.copy()

	@property
	def cycle(self):
		return self._cycle

	@property
	def pipeline(self):
		return self._pipeline
	

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

	def add_to_pipeline(self, method, position=None):
		"""
		Add a method to the existing pipeline
		method
			method to be added; should be part of the object
		position
			position of this method in the pipeline

		Note
		-----
		Internally, the pipeline is represented by a list
		and the position argument is a call to the 
		insert method of the list object
		"""
		if not(position):
			position = len(self._pipeline)
		self._pipeline.insert(position, getattr(self, method))

	def run(self):
		"""
		This should be the only method to call at a high level. 
		This method calls every method in the pipeline
		Must update the cycle after run
		"""
		for method in self._pipeline:
			method()
		self._cycle += 1