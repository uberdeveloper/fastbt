import unittest
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

		self.p = PipelineTest(10)

	def test_simple_run(self):
		## Should produce no output
		p = self.p
		p.run()	
		assert p.number == 10
		assert len(p.pipeline) == 4

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

	

