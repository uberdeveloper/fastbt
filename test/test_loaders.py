import pandas as pd
import sys
from sqlalchemy import create_engine
import unittest
import os
import shutil

sys.path.append('../')
from loaders import DataLoader

class TestLoader(unittest.TestCase):

	def test_create_hdf_file(self):		
		dl = DataLoader('eoddata', engine='test.h5',
			mode='HDF', tablename='eod')
		dl.load_data()
		print('NEW HDF5 FILE')
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





