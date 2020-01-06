import unittest
import random
import itertools
from fastbt.Meta import *

class TestMetaPipeline(unittest.TestCase):
	def setUp(self):
		class PipelineTest(TradingSystem):
			def __init__(self, number, **kwargs):
				super().__init__(**kwargs)
				self.number = number

			def add_10(self):
				self.number += 10

			def sub_4(self):
				self.number -= 4

			def mul_10(self):
				self.number *= 10

			def div_2(self):
				self.number = self.number/2

			def pow_2(self):
				self.number = self.number**2

			# The following functions are to check
			# positional and keyword arguments support

			def func1(self, a=5):
				self.number = self.number + a

			def func2(self, a, b=10):
				self.number = self.number + a - b

			def func3(self, *args):
				for i in args:
					self.number+=i

			def func4(self, **kwargs):
				for k,v in kwargs.items():
					self.number *= v


		self.p = PipelineTest(10)

	def test_simple_run(self):
		## Should produce no output
		p = self.p
		p.run()	
		assert p.number == 10
		assert len(p.pipeline) == 6

	def test_clear_pipeline(self):
		p = self.p
		p._pipeline = []
		p.run()
		assert len(p.pipeline) == 0

	def test_pipeline_1(self):
		p = self.p
		p.add_to_pipeline('add_10')
		p.add_to_pipeline('sub_4')
		p.run()
		assert p.number == 16
		p.add_to_pipeline('pow_2')
		p.add_to_pipeline('div_2')
		p.add_to_pipeline('mul_10')
		p.run()
		assert p.number == 2420

	def test_pipeline_1(self):
		p = self.p
		p._pipeline = []
		p.add_to_pipeline('add_10')
		p.add_to_pipeline('sub_4')
		p.add_to_pipeline('pow_2')
		p.add_to_pipeline('div_2')
		p.add_to_pipeline('mul_10')
		p.run()
		assert p.number == 1280
		# Reset number back; this is bad practice
		p.number = 10		
		p.add_to_pipeline('mul_10', 3)
		p.run()
		assert p.number == 12800

	def test_add_to_pipeline_no_function(self):
		p = self.p
		p.add_to_pipeline('unknown_func_1')
		p.add_to_pipeline('unknown_func_2')
		assert len(p.pipeline) == 6
		p.run()
		assert p.number == 10

	def test_add_to_pipeline_no_function_execution(self):
		p = self.p
		p.add_to_pipeline('add_10')
		for i in range(4):
			p._pipeline.append(('func_'+str(i), {}))
		p.add_to_pipeline('add_10')
		assert len(p.pipeline) == 12
		p.run()
		assert p.number == 30

	def test_add_to_pipeline_custom_insert(self):
		p = self.p
		p._pipeline = [('dummy', {})]
		p.add_to_pipeline('add_10')
		p.add_to_pipeline('mul_10', 1)
		p.run()
		assert p.number == 110

	def test_func_kwargs_1(self):
		p = self.p
		p.add_to_pipeline('func1')
		p.run()
		assert p.number == 15
		p.add_to_pipeline('func1', a=20)
		p.run()
		assert p.number == 40

	def test_func_kwargs_2(self):
		p = self.p
		p.add_to_pipeline('func4', a=2,b=3,c=4,d=10)
		p.run()
		assert p.number == 2400

	def test_func_kwargs_3(self):
		p = self.p
		p.add_to_pipeline('mul_10')
		p.add_to_pipeline('add_10', position=1)
		p.run()
		assert p.number == 200


class TestExtTradingSystem(unittest.TestCase):

	def setUp(self):
		self.ts = ExtTradingSystem

	def test_default_arguments(self):
		ts = self.ts()
		assert ts.MAX_GLOBAL_POSITIONS == 1	
		assert ts.MAX_QTY == 100

	def test_user_arguments(self):
		ts = self.ts(MAX_QTY=1000, MAX_GLOBAL_POSITIONS=2)
		assert ts.MAX_GLOBAL_POSITIONS == 2
		assert ts.MAX_QTY == 1000

	def test_argument_assignment(self):
		ts = self.ts()
		assert ts.MAX_GLOBAL_POSITIONS == 1
		ts.MAX_GLOBAL_POSITIONS = 10
		assert ts.MAX_GLOBAL_POSITIONS == 10

class TestExtTradingSystem_isEntry(unittest.TestCase):

	def setUp(self):
		self.ts = ExtTradingSystem(MAX_QTY=100, MAX_GLOBAL_POSITIONS=2)
		self.ts._symbol = None

	def test_max_qty_new_symbol(self):
		ts = self.ts
		ts._symbol = 'GOOG'
		assert ts.isEntry

	def test_max_qty(self):
		ts = self.ts
		ts._symbol = 'A'
		ts.tb.add_trade(1, 'A', 10, 50, 'B')
		assert ts.isEntry
		ts.tb.add_trade(2, 'A', 10, 120, 'S')
		assert ts.isEntry
		ts.tb.add_trade(3, 'A', 10, 200, 'B')
		assert not(ts.isEntry)

	def test_max_global_positions(self):
		ts = self.ts
		ts.tb.add_trade(1, 'A', 10, 50, 'B')
		ts._symbol = 'A'
		assert ts.isEntry
		ts._symbol = 'B'
		ts.tb.add_trade(2, 'B', 13, 70, 'S')
		assert not(ts.isEntry)
		# Live changing not recommended in production
		ts.MAX_GLOBAL_POSITIONS = 3
		assert ts.isEntry
		ts.tb.add_trade(3, 'C', 10,15, 'B')
		assert not(ts.isEntry)

class TestExtTradingSystem_add_trade(unittest.TestCase):

	def setUp(self):
		self.ts = ExtTradingSystem(MAX_GLOBAL_POSITIONS=3, symbol='GOOG')

	def test_add_trade_one_symbol(self):
		ts = self.ts
		ts.add_trade('B174')
		assert ts.tb.trades['GOOG'][0]['price'] == 174
		ts.add_trade('S110', qty=4)
		ts.add_trade('S120', qty=3)
		assert ts.tb.trades['GOOG'][1]['qty'] == -4
		ts._symbol = 'AAPL'
		ts.add_trade('B1128', qty=7)
		assert ts.tb.all_trades[-1]['qty'] == 7

class TestBrokerDictFilter(unittest.TestCase):
	def setUp(self):
		def f(it, n):
			return itertools.chain.from_iterable(itertools.repeat(it, n))
		A = f(['A','B', 'C'], 8)
		B = f([100,200,300,400], 6)
		C = f([1,2,3,4,5,6], 4)
		self.dct = [dict(x=x, y=y, z=z) for x,y,z in zip(A,B,C)]
		self.broker = Broker()

	def test_empty_dict(self):
		assert self.broker.dict_filter([]) == []

	def test_identity_dict(self):
		dct = [
			{'a': 15}, {'a': 20}, {'a': 10}
		]
		assert self.broker.dict_filter(dct) == dct

	def test_simple_dict(self):
		dct = [{'a': 15}, {'a': 20}, {'a': 10}]
		assert self.broker.dict_filter(dct, a=10) == [{'a': 10}]

	def test_no_matching_dict(self):
		assert self.broker.dict_filter(self.dct, y=1500) == []
		assert self.broker.dict_filter(self.dct, m=10) == []

	def test_filter_one(self):
		x = ['A'] * 8
		y = [100,400,300,200,100,400,300,200]
		z = [1,4,1,4,1,4,1,4]
		lst1 = [dict(x=a, y=b, z=c) for a,b,c in zip(x,y,z)]
		assert self.broker.dict_filter(self.dct, x='A') == lst1

	def test_filter_two(self):
		x = ['B'] * 4
		y = [100,300,100,300]
		z = [5] * 4
		lst1 = [dict(x=a, y=b, z=c) for a,b,c in zip(x,y,z)]
		assert self.broker.dict_filter(self.dct, z=5) == lst1

	def test_multi_filter(self):
		lst1 = [{'x': 'A', 'y':100, 'z': 1}] * 2
		assert self.broker.dict_filter(self.dct, x='A', y=100) == lst1

		lst2 = [{'x': 'B', 'y': 300, 'z': 5}] * 2
		assert self.broker.dict_filter(self.dct, x='B', y=300, z=5) == lst2
		assert self.broker.dict_filter(self.dct, x='B', y=300) == lst2




