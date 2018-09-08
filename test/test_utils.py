import pandas as pd
import pytest
import sys
sys.path.append('../')
from utils import *

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

def test_stop_loss():
	assert stop_loss(100, 3) == 97
	assert stop_loss(100, 3, order='S') == 103
	assert stop_loss(1013, 2.5, order='B', tick_size=0.1) == 987.7
	assert stop_loss(100, -3) == 103 # This should be depreceated
	assert stop_loss(100, -3, order='S') == 97

def test_stop_loss_error():
	with pytest.raises(ValueError):
		assert stop_loss(100, 3, 'BS')


	