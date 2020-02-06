"""
This module contains consolidated metrics
"""

import pandas as pd
import numpy as np
try:
	import pyfolio as pf
except ImportError:
	print('pyfolio not installed')

def spread_test(data, periods=['Y','Q','M']):
	"""
	Test whether the returns are spread over the entire period
	or consolidated in a single period
	data
		returns/pnl as series with date as index
	periods
		periods to check as list.
		all valid pandas date offset strings accepted

	returns a dataframe with periods as index and 
	profit/loss count and total payoff
	"""
	collect = []
	for period in periods:
		rsp = data.resample(period).sum()
		gt = rsp[rsp >= 0]
		lt = rsp[rsp < 0]
		values = (len(gt), gt.sum(), len(lt), lt.sum())
		collect.append(values)
	return pd.DataFrame(collect, index=periods, 
		columns=['num_profit', 'profit', 'num_loss', 'loss'])

def shuffled_drawdown(data, capital=1000):
	"""
	Calculate the shuffled drawdown for the given data
	"""
	np.random.shuffle(data)
	cum_p = data.cumsum() + capital
	max_p = np.maximum.accumulate(cum_p)
	diff = (cum_p - max_p)/capital
	return diff.min()

	