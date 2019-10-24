"""
This module contains consolidated metrics
"""

import pandas as pd
import numpy as np
try:
	import pyfolio as pf
except ImportError:
	print('pyfolio not installed')

def spread_test(data, periods=None):
	"""
	Test whether the returns are spread over the entire period
	or consolidated in a single period
	data
		returns/pnl as series with date as index
	periods
		periods to check
	"""
	pass
	