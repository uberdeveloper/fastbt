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
from intake.source.base import DataSource, Schema
import os

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

def percentage_bar(data, step):
	"""
	Generate the number of timesteps taken for each
	equivalent step in price
	data
		numpy 1d array
	step
		step size
	"""
	start = data[0]
	nextStep = start + step
	counter = 0
	steps = [start]
	period = [0]
	for d in data:
		if step >= 0:
			if d > nextStep:
				steps.append(nextStep)
				period.append(counter)
				nextStep += step
				counter = 0
			else:
				counter+=1
		elif step < 0:
			if d < nextStep:
				steps.append(nextStep)
				period.append(counter)
				nextStep += step
				counter = 0
			else:
				counter+=1

	# Final loop exit			
	steps.append(nextStep)
	period.append(counter)
	return (steps, period)		

def high_breach(s):
	"""
	Given a series of values, returns a series
	with consecutive highs as values and timestamp as index
	s
		series with timestamp as index
	"""
	highs = []
	ts = []
	max_val = 0
	index = s.index.values
	for i,v in enumerate(s.values):
		if v > max_val:
			highs.append(v)
			ts.append(index[i])
			max_val = v
	return pd.Series(highs, index=ts)


def low_breach(s):
	"""
	Given a series of values, returns a series
	with consecutive lows as values and timestamp as index
	s
		series with timestamp as index
	"""
	lows = []
	ts = []
	min_val = 1e+9 # Just setting an extreme value
	index = s.index.values
	for i,v in enumerate(s.values):
		if v < min_val:
			lows.append(v)
			ts.append(index[i])
			min_val = v
	return pd.Series(lows, index=ts)



class ExcelSource(DataSource):

	container = 'dataframe'
	name = 'excel_loader'
	version = '0.0.1'
	partition_access = True

	def __init__(self, filename, metadata=None):
		"""
		Initialize with filename and metadata
		"""
		self.filename = filename
		self._source = pd.ExcelFile(self.filename)
		super(ExcelSource, self).__init__(metadata=metadata)

	def _get_schema(self):
		sheets = self._source.sheet_names
		return Schema(
			datashape=None,
			dtype=None,
			shape=None,
			npartitions= len(sheets),
			extra_metadata = {'sheets': sheets}
			)

	def read_partition(self, sheet, **kwargs):
		"""
		Read a specific sheet from the list of sheets
		sheet
			sheet to read
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		if sheet in self.metadata.get('sheets', []):
			return self._source.parse(sheet, **kwargs)
		else:
			return 'No such sheet in the Excel File'

	def read(self, **kwargs):
		"""
		Read all sheets into a single dataframe.
		Sheetname is added as a column
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		sheets = self.metadata.get('sheets')
		collect = []
		if len(sheets) > 1:
			for sheet in sheets:
				temp = self.read_partition(sheet, **kwargs)
				temp['sheetname'] = sheet
				collect.append(temp)
		return pd.concat(collect, sort=False)

	def _close(self):
		self._source.close()


class HDFSource(DataSource):
	"""
	A simple intake container to load data from
	HDF5 fixed formats
	"""

	container = 'dataframe'
	name = 'HDF5_fixed_loader'
	version = '0.0.1'
	partition_access = True

	def __init__(self, directory, metadata=None, extension='h5'):
		"""
		Initialize with directory and metadata
		"""
		self.directory = directory
		self._ext = extension
		self._get_schema()
		super(HDFSource, self).__init__(metadata=metadata)

	def _get_schema(self):
		file_dict = {}	
		for root,directory,files in os.walk(self.directory):
			for file in files:
				filename = os.path.join(root, file)
				if filename.endswith(self._ext):
					file_dict[file] = filename
		return Schema(
			datashape=None,
			dtype=None,
			shape=None,
			npartitions= len(file_dict),
			extra_metadata = {
			'ext': self._ext,
			'src': self.directory,
			'files': file_dict
			}
			)

	def read_partition(self, file, **kwargs):
		"""
		Read a specific sheet from the list of sheets
		file
			filename without extension
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		ext = self.metadata.get('ext', self._ext)
		file = '{file}.{ext}'.format(file=file, ext=ext)
		if file in self.metadata.get('files', []):
			filename = self.metadata['files'][file]
			return pd.read_hdf(filename)
		else:
			return 'No such HDF file'

	def read(self, **kwargs):
		"""
		Read all sheets into a single dataframe.
		Sheetname is added as a column
		kwargs
			kwargs to the excel parse function
		"""
		self._load_metadata()
		print('Not implemented')

	def _close(self):
		print('Not implemented')


def twin_plot(data, y_axis, x_axis='timestamp'):
	"""
	Create a bokeh plot with twin axes
	"""
	from bokeh.plotting import figure
	from bokeh.models import LinearAxis, Range1d

	TOOLTIPS = [
	('datetime', '@x{%F %H:%M}'),
	('value', '$y{0.00}')
	]

	y1,y2 = y_axis[0], y_axis[1]
	h0 = data[y1].max()
	l0 = data[y1].min()
	h1 = data[y2].max()
	l1 = data[y2].min()
	p = figure(x_axis_type='datetime', y_range=(l0, h0),
		tooltips=TOOLTIPS, height=240, width=600)
	p.line(data[x_axis].values, data[y1].values, 
		color="red", legend=y1)
	p.extra_y_ranges = {"foo": Range1d(l1,h1)}
	p.line(data[x_axis], data[y2].values, color="blue", 
		y_range_name="foo", legend=y2)
	p.add_layout(LinearAxis(y_range_name="foo", axis_label=y2), 'left')
	p.hover.formatters= {'x': 'datetime'}
	p.legend.location = 'top_center'
	p.legend.click_policy = 'hide'
	return p


class OptionPayoff:
	"""
	A simple class for calculating option payoffs
	given spot prices and options
	1) Add your options with the add method
	2) Provide a spot price
	3) Call calculate to get the payoff for this spot price
	Note
	-----
	This class only does a simple arithmetic for the option and
	doesn't include any calculations for volatility or duration.
	It's assumed that the option is exercised at expiry and it
	doesn't have any time value
	"""
	def __init__(self):
		self._spot = 0
		self._options = []

	def _payoff(self, strike, option, position, **kwargs):
		"""
		calculate the payoff for the option
		"""
		comb = (option, position)
		spot = self._spot
		if comb == ('C', 'B'):
			return max(spot-strike, 0)
		elif comb == ('P', 'B'):
			return max(strike-spot, 0)
		elif comb == ('C', 'S'):
			return min(0, strike-spot)
		elif comb == ('P', 'S'):
			return min(0, spot-strike)

	def add(self, strike, opt_type='C', position='B', premium=0, qty=1):
		"""
		Add an option
		strike
			strike price of the options
		opt_type
			option type - C for call and P for put
		position
			whether you are Buying or Selling the option
			B for buy and S for sell
		premium
			option premium
		qty
			quantity of options contract
		"""
		if position == 'B':
			premium = 0-abs(premium)
		elif position == 'S':
			qty = 0-abs(qty)
		self._options.append({
			'strike': strike,
			'option': opt_type,
			'position': position,
			'premium': premium,
			'qty': qty
			})

	@property
	def options(self):
		"""
		return the list of options
		"""
		return self._options

	def clear(self):
		"""
		Clear all options
		"""
		self._options = []

	def spot(self, price):
		"""
		Set the spot price
		"""
		self._spot = price

	def calc(self):
		"""
		Calculate the payoff
		"""
		if self._spot <= 0:
			print('Spot price incorrect.\nSet the price with the spot method')
			return
		else:
			payoffs = []
			for p in self.options:
				profit = (self._payoff(**p) * abs(p['qty'])) + (p['premium'])
				payoffs.append(profit)
			return payoffs

def conditional(data, c1, c2, out=None):
	"""
	Create a conditional probability table with counts
	data
		dataframe
	c1
		condition as string
	c2
		list of conditions as strings
	out
		output format. If None, counts are returned.
		If a function is passed, it is applied to 
		each of the conditions and the return value
		of the function is stored for each condition.
		The function should have a single argument that
		takes a dataframe as an input.

	returns a dictionary with the conditions and
	the counts or the return value of each of the conditions
	Note
	----
	1. The dataframe is queried with c1 and each of the conditions
	in c2 are evaluated based on this result.
	2. All conditions are evaluated using `df.query`
	3. The condition strings should be valid columns in the dataframe
	4. The function passed should have a single argument, the dataframe.
	"""
	dct = {}
	if out is None:
		out = len
	df = data.query(c1)
	dct[c1] = out(df)
	for c in c2:
		dct[c] = out(df.query(c))
	return dct


class Catalog:
	"""
	A intake catalog creator
	The catalog is created in the following manner
		1. All files in the root directory are considered to
		be separate files and loaded as such.
		2. All directories and subdirectories inside the root 
		directory are considered to be separate data sources
		3. Each of the files are matched against the extension
		name and the corresponding mapper
		4. Files inside a directory are randomly selected and the
		file type is determined for the entire directory.
		**It's assumed that all files inside any sub-directories
		are of the same file type**
	"""
	def __init__(self, directory):
		"""
		directory
			directory to search for files
		"""
		self._directory = directory
		"""
		**filetypes** is a dictionary with the file type as
		key and a sub-dictionary with driver and extensions
		as keys and the corresponding driver and extensions
		as values. 
		It is a logical structure that maps a file type to
		its intake driver and possible extensions since each
		file type can have more than one extension. This
		dictionary is looped to get the self._mappers for each
		extension.
		**Assumed each filetype has a single driver but more than
		one extension**
		"""
		filetypes = {
			'excel': {
				'driver': 'fast.experimental.ExcelSource',
				'extensions': ['xls', 'xlsx']
			},
			'csv': {
				'driver': 'intake.source.csv.CSVSource',
				'extensions': ['csv', 'txt']
			}
		}
		self._mappers =  {}
		for k,v in filetypes.items():
			for ext in v['extensions']:
				self._mappers[ext] = v['driver']
	

	def generate_catalog(self):
		"""
		Generate catalog
		"""
		dct = {}
		dct['sources'] = {}
		src = dct['sources']
		for root,folder,files in os.walk(self._directory):
			for file in files:
				ext = file.split('.')[-1]
				if ext in self._mappers:
					src[file.split('.')[0]] = {
						'args': {
							'urlpath': os.path.join(root, file)
						}						,
						'driver': self._mappers[ext],
						'description': '',
						'metadata': {}
					}
		return dct
			
