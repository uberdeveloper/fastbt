"""
This is an experimental module.
Everything in this module is untested and probably incorrect.
Don't use them.

This is intended to be a place to develop new functions instead of
having an entirely new branch
"""
import pandas as pd 
import numpy as np
from numba import jit, njit

@jit
def v_cusum(array):
	"""
	Calcuate cusum - numba version
	array
		numpy array
	returns
		pos and neg arrays
	""" 
	L = len(array)
	pos = [0]
	neg = [0]
	pos_val = 0
	neg_val = 0
	d = np.diff(array)[1:]
	for i in d:
		if i >= 0:
			pos_val += i
		else:
			neg_val += i
		pos.append(pos_val)
		neg.append(neg_val)
	return (pos, neg)

@jit
def sign_change(array):
	"""
	Calcuate the sign change in an array
	If the current value is positive and previous value negative, mark as 1.
	If the current value is negative and previous value positive, mark as -1.
	In case of no change in sign, mark as 0
	"""
	L = len(array)
	arr = np.empty(L)
	arr[0] = 0
	for i in range(1, L):
		# TO DO: Condition not handling edge case
		if (array[i] >= 0) & (array[i-1] < 0):
			arr[i] = 1
		elif (array[i] <= 0) & (array[i-1] > 0):
			arr[i] = -1
		else:
			arr[i] = 0
	return arr


def cusum(array):
	"""
	Calcuate cusum
	array
		a pandas series with a timestamp or datetime index
	The cusum is just an aggregate of positive and negative differences
	returns
		pandas dataframe with positive and negative cumulatives,
		ratio, differences, regime change along with the original index
	"""
	pos = [0]
	neg = [0]
	pos_val = 0
	neg_val = 0
	d = array.diff()[1:]
	for i in d:
		if i >= 0:
			pos_val += i
		else:
			neg_val += i
		pos.append(pos_val)
		neg.append(neg_val)
	df = pd.DataFrame({'pos': pos, 'neg': neg}, index=array.index)
	df['neg'] = df['neg'].abs()
	df['d'] = df['pos'] - df['neg']
	df['reg'] = sign_change(df.d.values)
	df['ratio'] = df['pos'] / df['neg']
	return df




