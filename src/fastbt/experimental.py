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

	datetime_tip = '@{}'.format(x_axis) + '{%F %H:%M}'
	print(datetime_tip)

	TOOLTIPS = [
	('datetime', '@x{%F %H:%M}'),
	('value', '$y{0.0}')
	]

	y1,y2 = y_axis[0], y_axis[1]
	h0 = data[y1].max()
	l0 = data[y1].min()
	h1 = data[y2].max()
	l1 = data[y2].min()
	p = figure(x_axis_type='datetime', y_range=(l0, h0),
		tooltips=TOOLTIPS)
	p.line(data[x_axis].values, data[y1].values, color="red")
	p.extra_y_ranges = {"foo": Range1d(l1,h1)}
	p.line(data[x_axis], data[y2].values, color="blue", y_range_name="foo")
	p.add_layout(LinearAxis(y_range_name="foo", axis_label=y2), 'left')
	p.hover.formatters= {'x': 'datetime'}
	return p


