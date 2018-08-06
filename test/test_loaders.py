import pandas as pd
import sys
from sqlalchemy import create_engine
import unittest
import os
import shutil
from numpy import dtype

sys.path.append('../')
from loaders import DataLoader

class TestLoader(unittest.TestCase):

	def test_create_hdf_file(self):		
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		dl.load_data()
		self.assertEqual(len(pd.read_hdf('test.h5', 'data/eod')), 10030)
		self.assertEqual(len(pd.read_hdf('test.h5', 'updated/eod')), 5)				

	def test_create_database(self):
		engine = create_engine('sqlite:///test.sqlite')
		dl = DataLoader('eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		dl.load_data()
		self.assertEqual(len(pd.read_sql_table('eod', engine)), 10030)
		self.assertEqual(len(pd.read_sql_table('updated_eod', engine)), 5)

	def test_run_loader_multiple_times(self):
		dl = DataLoader('eoddata', engine='test.h5',
		mode='HDF', tablename='eod')
		for i in range(5):
			dl.load_data()
		engine = create_engine('sqlite://')
		dl = DataLoader('eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		for i in range(5):
			dl.load_data()
		shape_hdf = len(pd.read_hdf('test.h5', 'data/eod'))
		shape_sql = len(pd.read_sql_table('eod', engine))
		self.assertEqual(shape_hdf, shape_sql)
		self.assertEqual(shape_hdf, 12053)

	def test_existing_hdf_file(self):
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		shutil.copy2('eoddata/INDEX_20180731.txt', 
					'eoddata/INDEX_20000000.txt')
		dl.load_data()
		self.assertEqual(len(pd.read_hdf('test.h5', 'data/eod')), 12053)
		self.assertEqual(len(pd.read_hdf('test.h5', 'updated/eod')), 6)		


	def test_existing_database(self):
		engine = create_engine('sqlite:///test.sqlite')
		dl = DataLoader('eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		shutil.copy2('eoddata/INDEX_20180731.txt', 
					'eoddata/INDEX_20000000.txt')
		dl.load_data()
		self.assertEqual(len(pd.read_sql_table('eod', engine)), 12053)
		self.assertEqual(len(pd.read_sql_table('updated_eod', engine)), 6)


	def test_wrong_mode(self):
		dl = DataLoader('eoddata', engine='test.h5',
			mode='SQL', tablename='eod')
		with self.assertRaises(Exception):
			dl.load_data()

		with self.assertRaises(TypeError):
			DataLoader('eoddata', engine='some_random_mode',
				mode='CSV', tablename='eod')


	@classmethod
	def tearDownClass(self):
		os.remove('test.h5')
		os.remove('test.sqlite')
		os.remove('eoddata/INDEX_20000000.txt')


def test_HDF_rename_columns():
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		rename =  {
			'<ticker>': 'symbol',
			'<date>': 'date',
			'<open>': 'open',
			'<high>': 'high',
			'<low>': 'low',
			'<close>': 'close',
			'<vol>': 'vol'
			}
		dl.load_data(columns=rename)
		df = pd.read_hdf('test.h5', 'data/eod')
		assert len(df) == 10030
		assert len(pd.read_hdf('test.h5', 'updated/eod')) == 5
		cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'vol']
		for x,y in zip(df.columns, cols):
			assert x == y
		os.remove('test.h5')

def test_SQL_rename_columns():
		engine = create_engine('sqlite://')
		dl = DataLoader('eoddata', engine=engine, 
			mode='SQL', tablename='eod')
		rename =  {
			'<ticker>': 'symbol',
			'<date>': 'date',
			'<open>': 'open',
			'<high>': 'high',
			'<low>': 'low',
			'<close>': 'close',
			'<vol>': 'vol'
			}
		dl.load_data(columns=rename)
		df = pd.read_sql_table('eod', engine)
		assert len(df) == 10030
		cols = ['symbol', 'date', 'open', 'high', 'low', 'close', 'vol']
		for x,y in zip(df.columns, cols):
			assert x == y

def test_HDF_parse_dates():
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		rename =  {
			'<ticker>': 'symbol',
			'<date>': 'date',
			'<open>': 'open',
			'<high>': 'high',
			'<low>': 'low',
			'<close>': 'close',
			'<vol>': 'vol'
			}
		dl.load_data(columns=rename, parse_dates=['<date>'])
		df = pd.read_hdf('test.h5', 'data/eod')
		assert df.dtypes['date'] == dtype('<M8[ns]')
		os.remove('test.h5')

def test_HDF_parse_dates_auto():
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		rename =  {
			'<ticker>': 'symbol',
			'<date>': 'date',
			'<open>': 'open',
			'<high>': 'high',
			'<low>': 'low',
			'<close>': 'close',
			'<vol>': 'vol'
			}
		dl.load_data(columns=rename)
		df = pd.read_hdf('test.h5', 'data/eod')
		assert df.dtypes['date'] == dtype('<M8[ns]')
		os.remove('test.h5')

def test_HDF_post_func():
	dl = DataLoader('eoddata', engine='test.h5',
		mode='HDF', tablename='eod')
	rename =  {
			'<ticker>': 'symbol',
			'<date>': 'date',
			'<open>': 'open',
			'<high>': 'high',
			'<low>': 'low',
			'<close>': 'close',
			'<vol>': 'vol'
			}
	def add_filename(x,y,z):
		x['filename'] = y
		x['avgprice'] = (x['<open>'] + x['<close>'])/2
		return x
	dl.load_data(columns=rename, postfunc=add_filename)
	df = pd.read_hdf('test.h5', 'data/eod')




		
