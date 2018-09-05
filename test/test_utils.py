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

def test_max_limit():
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
