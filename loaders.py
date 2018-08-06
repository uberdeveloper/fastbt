"""
Load data to database
"""

import os
import pandas as pd

#from .utils import *

PATH = '/home/machine/Projects/finance/data/other'
CONSTITUENTS_FILE = os.path.join(PATH, 'IndexConstituents.xlsx')
CHANGES_FILE = os.path.join(PATH, 'IndexChanges.xlsx')
SYMBOL_LOOKUP_FILE = os.path.join(PATH, 'symbol_lookup.csv')

def load_indices_data(indices_file, constituents_file, changes_file,
                        symbol_lookup_file, on='Company', path='indices',
                        key=['Inclusion into Index', 'Exclusion from Index']):
    """
    Load indices into database
    indices file
        A HDF5 file to load data into
    constituents file
        An Excel file with different indices as sheet names
    changes file
        An Excel file with changes in the required format
    symbol_lookup_file
        A csv file containing the company and symbol names
    """
    constituents = pd.read_excel(constituents_file, sheet_name=None)
    changes = pd.read_excel(changes_file, sheet_name=None,
    index_col=1, parse_dates=True)
    lookup = pd.read_csv(SYMBOL_LOOKUP_FILE, parse_dates=['First Listing Date'])
    for k,v in constituents.items():
        symbols = list(v['Company Name'])
        chg = changes[k]
        idx = pd.DataFrame(generate_index('2012-01-01', '2018-06-01', symbols, chg),
                            columns=['timestamp', 'Company'])
        df = idx.merge(lookup)
        df.to_hdf(indices_file, path+'/'+k)
        print(k)      


class DataLoader(object):
    """
    Data Loader class
    """
    def __init__(self, directory, mode='HDF', engine=None, 
                 tablename=None, parse_dates=[]):
        """
        Initialize parameters
        directory
            directory to search files
        mode
            HDF/SQL - should be explicitly specified
        engine
            filename in case of HDF
            SQL Alchemy connection string in case of engine
        tablename
            table where data is to be written
        parse dates
            list of columns to be parsed as date
        """
        if mode not in ['SQL', 'HDF']:
            raise TypeError('No mode specified; should be HDF or SQL')
        self.directory = directory
        self.mode = mode
        self.engine = engine
        self.tablename = tablename
        if type(parse_dates) != list:
            raise TypeError('parse dates should be a list')
        self._parse_dates = parse_dates
        
    def _initialize_HDF_file(self):
        import hashlib
        hash = hashlib.sha1().hexdigest()
        with pd.HDFStore(self.engine) as store:
            s = pd.Series(['hash'*2])            
            if len(store.keys()) == 0:
                store.append('updated/'+self.tablename, s)

    def _write_to_HDF(self, **kwargs):
        """
        Write data to HDF file
        """
        update_table = '/updated/' + self.tablename
        data_table = '/data/' + self.tablename
        updated_list = []
        with pd.HDFStore(self.engine) as store:
            if update_table in store.keys():
                updated_list = store.get(update_table).values

        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, parse_dates = self._parse_dates, **kwargs)
                    df = df.rename(str.lower, axis='columns')
                    df.to_hdf(self.engine, key=data_table, format='table',
                        append=True, data_columns=True)
                    # Updating the file data
                    pd.Series([file]).to_hdf(self.engine, key=update_table,
                        format='table', append=True)

    def _write_to_SQL(self, **kwargs):
        """
        Write data to SQL database     
        """
        update_table = 'updated_' + self.tablename
        data_table = self.tablename
        updated_list = []
        if self.engine.has_table(update_table):
            updated_list = pd.read_sql_table(update_table, self.engine).values

        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, parse_dates = self._parse_dates, **kwargs)
                    df = df.rename(str.lower, axis='columns')
                    s = pd.Series([file])
                    df.to_sql(data_table, con=self.engine, if_exists='append',
                    index=False, chunksize=1500)
                    # Updating the file data
                    s.to_sql(update_table, con=self.engine, if_exists='append', 
                        index=False, chunksize=1500)

    def load_data(self, **kwargs):
        """
        Load data into database
        """
        if self.mode == 'HDF':
            self._write_to_HDF(**kwargs)
        else:
            self._write_to_SQL(**kwargs)