import pandas as pd
from sqlalchemy import create_engine
import unittest
import os
import shutil
import tempfile
from numpy import dtype
import pytest
from math import isclose
from random import randint
import context

from fastbt.loaders import DataLoader, apply_adjustment, collate_data

def compare(frame1, frame2):
    """
    Compare a random value from 2 dataframes
    return
        True if values are equal else False
    """
    r1 = randint(0, len(frame1)-1)
    r2 = randint(0, len(frame1.columns) - 1)
    return frame1.iloc[r1, r2] == frame2.iloc[r1, r2]


class TestLoader(unittest.TestCase):

	def test_create_hdf_file(self):
		with tempfile.NamedTemporaryFile() as fp:		
			dl = DataLoader('tests/data/eoddata', engine=fp.name,
				mode='HDF', tablename='eod')
			dl.load_data()
			self.assertEqual(len(pd.read_hdf(fp.name, 'data/eod')), 10030)
			self.assertEqual(len(pd.read_hdf(fp.name, 'updated/eod')), 5)				

	def test_create_database(self):
		engine = create_engine('sqlite://')
		dl = DataLoader('tests/data/eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		dl.load_data()
		self.assertEqual(len(pd.read_sql_table('eod', engine)), 10030)
		self.assertEqual(len(pd.read_sql_table('updated_eod', engine)), 5)

	def test_run_loader_multiple_times(self):
		with tempfile.NamedTemporaryFile() as fp:
			dl = DataLoader('tests/data/eoddata', engine=fp.name,
			mode='HDF', tablename='eod')
			for i in range(5):
				dl.load_data()
			engine = create_engine('sqlite://')
			dl = DataLoader('tests/data/eoddata', engine=engine, 
				mode='SQL', tablename='eod')
			for i in range(5):
				dl.load_data()
			shape_hdf = len(pd.read_hdf(fp.name, 'data/eod'))
			shape_sql = len(pd.read_sql_table('eod', engine))
			self.assertEqual(shape_hdf, shape_sql)
			self.assertEqual(shape_hdf, 12053)

	def test_existing_hdf_file(self):
		with tempfile.NamedTemporaryFile() as fp:
			dl = DataLoader('tests/data/eoddata', engine=fp.name,
				mode='HDF', tablename='eod')
			shutil.copy2('tests/data/eoddata/INDEX_20180731.txt', 
						'tests/data/eoddata/INDEX_20000000.txt')
			dl.load_data()
			self.assertEqual(len(pd.read_hdf(fp.name, 'data/eod')), 12053)
			self.assertEqual(len(pd.read_hdf(fp.name, 'updated/eod')), 6)		


	def test_existing_database(self):
		engine = create_engine('sqlite://')
		dl = DataLoader('tests/data/eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		shutil.copy2('tests/data/eoddata/INDEX_20180731.txt', 
					 'tests/data/eoddata/INDEX_20000000.txt')
		dl.load_data()
		self.assertEqual(len(pd.read_sql_table('eod', engine)), 12053)
		self.assertEqual(len(pd.read_sql_table('updated_eod', engine)), 6)


	def test_wrong_mode(self):
		with tempfile.NamedTemporaryFile() as fp:
			dl = DataLoader('tests/data/eoddata', engine=fp.name,
				mode='SQL', tablename='eod')
			with self.assertRaises(Exception):
				dl.load_data()

		with self.assertRaises(TypeError):
			DataLoader('tests/data/eoddata', engine='some_random_mode',
				mode='CSV', tablename='eod')


	@classmethod
	def tearDownClass(self):
		os.remove('tests/data/eoddata/INDEX_20000000.txt')

# rename columns
rename =  {
	'<ticker>': 'symbol',
	'<date>': 'date',
	'<open>': 'open',
	'<high>': 'high',
	'<low>': 'low',
	'<close>': 'close',
	'<vol>': 'vol'
	}

def test_HDF_rename_columns():
	with tempfile.NamedTemporaryFile() as fp:
		dl = DataLoader('tests/data/eoddata', engine=fp.name,
			mode='HDF', tablename='eod')
		dl.load_data(columns=rename)
		df = pd.read_hdf(fp.name, 'data/eod')
		assert len(df) == 10030
		assert len(pd.read_hdf(fp.name, 'updated/eod')) == 5
		cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'vol']
		for x,y in zip(df.columns, cols):
			assert x == y

def test_SQL_rename_columns():
	engine = create_engine('sqlite://')
	dl = DataLoader('tests/data/eoddata', engine=engine, 
		mode='SQL', tablename='eod')
	dl.load_data(columns=rename)
	df = pd.read_sql_table('eod', engine)
	assert len(df) == 10030
	cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'vol']
	for x,y in zip(df.columns, cols):
		assert x == y

def test_HDF_parse_dates():
	with tempfile.NamedTemporaryFile() as fp: 
		dl = DataLoader('tests/data/eoddata', engine=fp.name,
			mode='HDF', tablename='eod')
		dl.load_data(columns=rename, parse_dates=['<date>'])
		df = pd.read_hdf(fp.name, 'data/eod')
		assert df.dtypes['date'] == dtype('<M8[ns]')

def test_SQL_parse_dates():
	engine = create_engine('sqlite://')
	dl = DataLoader('tests/data/eoddata', engine=engine, 
		mode='SQL', tablename='eod')
	dl.load_data(columns=rename, parse_dates=['<date>'])
	df = pd.read_sql_table('eod', engine)
	assert df.dtypes['date'] == dtype('<M8[ns]')

def test_HDF_parse_dates_auto():
	with tempfile.NamedTemporaryFile() as fp:
		dl = DataLoader('tests/data/eoddata', engine=fp.name,
			mode='HDF', tablename='eod')
		dl.load_data(columns=rename)
		df = pd.read_hdf(fp.name, 'data/eod')
		assert df.dtypes['date'] == dtype('<M8[ns]')

def test_SQL_parse_dates_auto():
	engine = create_engine('sqlite://')
	dl = DataLoader('tests/data/eoddata', engine=engine, 
		mode='SQL', tablename='eod')
	dl.load_data(columns=rename)
	df = pd.read_sql_table('eod', engine)
	assert df.dtypes['date'] == dtype('<M8[ns]')

def test_HDF_post_func():
	with tempfile.NamedTemporaryFile() as fp:
		dl = DataLoader('tests/data/eoddata', engine=fp.name,
			mode='HDF', tablename='eod')
		def add_filename(x,y,z):
			x['filename'] = y
			x['avgprice'] = (x['open'] + x['close'])/2
			return x
		dl.load_data(columns=rename, postfunc=add_filename)
		df = pd.read_hdf(fp.name, 'data/eod')
		assert df.dtypes['date'] == dtype('<M8[ns]')
		assert df.shape[1] == 9
		assert 'filename' in df.columns
		assert 'avgprice' in df.columns

def test_SQL_post_func():
	engine = create_engine('sqlite://')
	dl = DataLoader('tests/data/eoddata', engine=engine, 
		mode='SQL', tablename='eod')
	def add_filename(x,y,z):
		x['filename'] = y
		x['avgprice'] = (x['open'] + x['close'])/2
		return x
	dl.load_data(columns=rename, postfunc=add_filename)
	df = pd.read_sql_table('eod', engine)
	assert df.dtypes['date'] == dtype('<M8[ns]')
	assert df.shape[1] == 9
	assert 'filename' in df.columns
	assert 'avgprice' in df.columns

def test_apply_adj_mul():
	df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
	adj_df = apply_adjustment(df, adj_date='2018-07-21', 
			adj_value=1/2)
	adj_df = adj_df.set_index('date').sort_index()
	cols = ['open', 'high', 'low', 'close']
	assert adj_df.loc['2018-07-11', 'open'] == 3151.24
	assert adj_df.loc['2018-07-21', 'close'] == 3702.15
	for a,b in zip(adj_df.loc['2018-07-21', cols] ,
		(3665.27, 3721.2, 3608.47, 3702.15)):
		assert a == b
	assert adj_df.loc['2018-08-01', 'high'] == 15500.16
	assert adj_df.loc['2018-07-11', 'volume'] == 2481016

def test_apply_adj_sub():
	df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
	adj_df = apply_adjustment(df, adj_date='2018-08-01', 
			adj_value=100, adj_type='sub')
	adj_df = adj_df.set_index('date').sort_index()
	assert adj_df.loc['2018-07-16', 'close'] == 6626.4
	assert adj_df.loc['2018-08-01', 'high'] == 15500.16
	assert adj_df.loc['2018-08-10', 'close'] == 12286.6

def test_apply_adj_sub_negative():
	df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
	adj_df = apply_adjustment(df, adj_date='2018-08-01', 
			adj_value=-100, adj_type='sub')
	adj_df = adj_df.set_index('date').sort_index()
	assert adj_df.loc['2018-07-16', 'close'] == 6826.4
	assert adj_df.loc['2018-08-01', 'high'] == 15500.16
	assert adj_df.loc['2018-08-10', 'close'] == 12286.6

def test_apply_adj_raise_error():
	with pytest.raises(ValueError):
		df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
		adj_df = apply_adjustment(df, adj_date='2018-08-01', 
			adj_value=-100, adj_type='div')

def test_apply_adj_date_col():
	df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
	df['timestamp'] = df['date']
	del df['date']
	adj_df = apply_adjustment(df, adj_date='2018-07-21', 
			adj_value=1/2, date_col='timestamp')
	adj_df = adj_df.set_index('timestamp').sort_index()
	assert adj_df.loc['2018-07-11', 'open'] == 3151.24
	assert adj_df.loc['2018-07-21', 'close'] == 3702.15

def test_apply_adj_cols():
	df = pd.read_csv('tests/data/BTC.csv', parse_dates=['date'])
	adj_df = apply_adjustment(df, adj_date='2018-07-21', 
			adj_value=1/2, cols=['open', 'high'])
	adj_df = adj_df.set_index('date').sort_index()
	cols = ['open', 'high', 'low', 'close']
	assert adj_df.loc['2018-07-11', 'open'] == 3151.24
	assert adj_df.loc['2018-07-11', 'close'] == 6381.87

def test_apply_split_SQL_dataloader():
	engine = create_engine('sqlite://')
	dl = DataLoader(directory='tests/data/NASDAQ/data', mode='SQL',
		engine=engine, tablename='eod')
	dl.load_data()
	dl.apply_splits(directory='tests/data/NASDAQ/adjustments/')
	df = pd.read_sql_table('eod', engine)
	result = pd.read_csv('NASDAQ/nasdaq_results.csv', parse_dates=['date'])
	splits = pd.read_csv('tests/data/NASDAQ/adjustments/splits.csv',
		parse_dates=['date'])
	for i, row in splits.iterrows():
		sym = row.at['symbol']
		cond = 'symbol == "{}"'.format(sym)
		frame1 = df.query(cond).sort_values(by='date').reset_index(drop=True)
		frame2 = result.query(cond).sort_values(by='date').reset_index(drop=True)
		L = len(frame1)
		cols = frame1.columns
		for i in range(L):
			for j in cols:
				if j in ['open', 'high', 'low', 'close', 'volume']:
					a = frame1.loc[i,j]
					b = frame2.loc[i,j]
					assert isclose(a,b,abs_tol=0.015)
				else:
					assert frame1.loc[i,j] == frame2.loc[i,j]

def test_apply_split_SQL_dataloader():
	engine = create_engine('sqlite://')
	dl = DataLoader(directory='tests/data/NASDAQ/data', mode='SQL',
		engine=engine, tablename='eod')
	dl.load_data()
	dl.apply_splits(directory='tests/data/NASDAQ/adjustments/')
	df = pd.read_sql_table('eod', engine)
	result = pd.read_csv('tests/data/NASDAQ/nasdaq_results.csv', parse_dates=['date'])
	splits = pd.read_csv('tests/data/NASDAQ/adjustments/splits.csv',
		parse_dates=['date'])
	for i, row in splits.iterrows():
		sym = row.at['symbol']
		cond = 'symbol == "{}"'.format(sym)
		frame1 = df.query(cond).sort_values(by='date').reset_index(drop=True)
		frame2 = result.query(cond).sort_values(by='date').reset_index(drop=True)
		L = len(frame1)
		cols = frame1.columns
		for i in range(L):
			for j in cols:
				if j in ['open', 'high', 'low', 'close', 'volume']:
					a = frame1.loc[i,j]
					b = frame2.loc[i,j]
					assert isclose(a,b,abs_tol=0.015)
				else:
					assert frame1.loc[i,j] == frame2.loc[i,j]


def test_apply_split_HDF_dataloader():
	with tempfile.NamedTemporaryFile() as fp:
		engine = fp.name
		dl = DataLoader(directory='tests/data/NASDAQ/data', mode='HDF',
			engine=engine, tablename='eod')
		dl.load_data()
		dl.apply_splits(directory='tests/data/NASDAQ/adjustments/')
		df = pd.read_hdf(engine, 'data/eod')
		result = pd.read_csv('tests/data/NASDAQ/nasdaq_results.csv', parse_dates=['date'])
		splits = pd.read_csv('tests/data/NASDAQ/adjustments/splits.csv',
			parse_dates=['date'])
		for i, row in splits.iterrows():
			sym = row.at['symbol']
			cond = 'symbol == "{}"'.format(sym)
			frame1 = df.query(cond).sort_values(by='date').reset_index(drop=True)
			frame2 = result.query(cond).sort_values(by='date').reset_index(drop=True)
			L = len(frame1)
			cols = frame1.columns
			for i in range(L):
				for j in cols:
					if j in ['open', 'high', 'low', 'close', 'volume']:
						a = frame1.loc[i,j]
						b = frame2.loc[i,j]
						print(a,b,sym)
						assert isclose(a,b,abs_tol=0.015)
					else:
						assert frame1.loc[i,j] == frame2.loc[i,j]

def test_collate_data():
	df = collate_data('tests/data/NASDAQ/data', parse_dates=['Date'])
	df = df.rename(lambda x: x.lower(), axis='columns')
	df = df.sort_values(by=['date', 'symbol'])
	engine = create_engine('sqlite://')
	dl = DataLoader(directory='tests/data/NASDAQ/data', mode='SQL',
		engine=engine, tablename='eod')
	dl.load_data()
	df2 = pd.read_sql_table('eod', engine).sort_values(by=['date', 'symbol'])
	assert len(df) == len(df2)
	for i in range(100):
		assert compare(df, df2)

def test_collate_data_function():
	def f(x):
		return pd.read_csv(x).iloc[:10, :3]
	df = collate_data('tests/data/NASDAQ/data', function=f)
	assert len(df) == 80
	assert df.shape == (80, 3)