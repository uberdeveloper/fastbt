"""
Load data to database
"""

import os
import pandas as pd

def apply_adjustment(df, adj_date, adj_value,
                    adj_type='mul',date_col='date',
                    cols=['open','high', 'low', 'close']):
    """
    Apply adjustment to a given stock
    df
        dataframe of the given stock
    adj_date
        date from which the adjustment is
        to be made
    adj_value
        value to be adjusted
    adj_type
        method of adjustment **mul/sub**
        mul means multiply all the values
            such as splits and bonuses
        sub means subtract the values
            such as dividends
 
    date_col
        date column  on which the adjustment
        is to be applied
    cols
        columns to which the adjustment is to
        be made

    Notes
    -----
    1) You can use negative values to add to the
    stock value by using **adj_type=sub**
    2) Adjustment is applied prior to all dates
    in the dataframe
    3) In case your dataframe has date or
    symbol as indexes, reset them
    """
    df = df.set_index(date_col).sort_index()
    values_on_adj_date = df.loc[adj_date, cols].copy()
    if adj_type == "mul":
        adjusted_values = (df.loc[:adj_date, cols] * adj_value).round(2)
    elif adj_type == "sub":
        adjusted_values = (df.loc[:adj_date, cols] - adj_value).round(2)
    else:
        raise ValueError('adj_type should be either mul or sub')
    df.loc[:adj_date, cols] = adjusted_values
    df.loc[adj_date, cols] = values_on_adj_date
    return df.reset_index()    

class DataLoader(object):
    """
    Data Loader class
    """
    def __init__(self, directory, mode='HDF', engine=None, 
                 tablename=None):
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

        if kwargs.get('columns'):
            columns = kwargs.pop('columns')
        else:
            columns = None

        if kwargs.get('parse_dates'):
            parse_dates = kwargs.get('parse_dates')
        else:
            parse_dates = None

        if kwargs.get('postfunc'):
            postfunc = kwargs.pop('postfunc')
        else:
            postfunc = None


        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, **kwargs)       
                    df = df.rename(str.lower, axis='columns')
                    if columns:
                        df = df.rename(columns, axis='columns')
                    if not(parse_dates):
                        date_cols = ['date', 'time', 'datetime', 'timestamp']
                        for c in df.columns:
                            if c in date_cols:
                                df[c] = pd.to_datetime(df[c])
                    if postfunc:
                        df = postfunc(df, file, root)
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

        if kwargs.get('columns'):
            columns = kwargs.pop('columns')
        else:
            columns = None

        if kwargs.get('parse_dates'):
            parse_dates = kwargs.get('parse_dates')
        else:
            parse_dates = None

        if kwargs.get('postfunc'):
            postfunc = kwargs.pop('postfunc')
        else:
            postfunc = None

        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, **kwargs)
                    df = df.rename(str.lower, axis='columns')
                    if columns:
                        df = df.rename(columns, axis='columns')
                    if not(parse_dates):
                        date_cols = ['date', 'time', 'datetime', 'timestamp']
                        for c in df.columns:
                            if c in date_cols:
                                df[c] = pd.to_datetime(df[c])
                    if postfunc:
                        df = postfunc(df, file, root)
                    s = pd.Series([file])
                    df.to_sql(data_table, con=self.engine, if_exists='append',
                    index=False, chunksize=1500)
                    # Updating the file data
                    s.to_sql(update_table, con=self.engine, if_exists='append', 
                        index=False, chunksize=1500)

    def load_data(self, **kwargs):
        """
        Load data into database
        kwargs
        columns
            column names as dictionary
            with key being column name from file
            and value being the column to be renamed
            ```
            {'OPENING': 'open', 'CLOSING': 'close'}
            ```
        parse_dates
            columns to be parsed as list
            If not given, any column with name
            date, datetime, time, timestamp is 
            automatically parse
        postfunc
            function to be run after reading the csv file  
        kwargs
            Any other arguments to the pandas read_csv function          
        """
        if self.mode == 'HDF':
            self._write_to_HDF(**kwargs)
        else:
            self._write_to_SQL(**kwargs)

    def apply_splits(self, directory='adjustments', 
        filename='splits.csv', symbol='symbol', timestamp='date'):
        """
        Apply splits recursively
        By default, only open, high, low, close and volume columns
        are modified
        """

        filename = os.path.join(directory, filename)
        try:
            splits = pd.read_csv(filename, parse_dates=[timestamp])
        except Exception as e:
            print(e)

        if self.mode == 'SQL':
            df = pd.read_sql_table(self.tablename, self.engine)
            for i, row in splits.iterrows():
                q = 'symbol == "{sym}"'
                temp = df.query(q.format(sym=row.at[symbol]))
                params = {
                    'adj_date': row.at[timestamp],
                    'adj_value': row.at['from']/row.at['to'],
                    'adj_type': 'mul',
                    'date_col': timestamp,
                    'cols': ['open', 'high', 'low', 'close']
                }
                temp = apply_adjustment(temp, **params)
                params.update({
                    'adj_value': row.at['to'] / row.at['from'],
                    'cols': ['volume']
                    })
                temp = apply_adjustment(temp, **params)
                cols = ['open', 'high', 'low', 'close', 'volume']
                temp.index = df.loc[df[symbol] == row.at[symbol]].index
                df.loc[temp.index] = temp
            df.to_sql(self.tablename, self.engine, if_exists='replace', index=False)
        elif self.mode == 'HDF':          
            df = pd.read_hdf(self.engine, '/data/'+ self.tablename)
            df.index = range(len(df))
            for i, row in splits.iterrows():
                q = 'symbol == "{sym}"'
                temp = df.query(q.format(sym=row.at[symbol]))
                params = {
                    'adj_date': row.at[timestamp],
                    'adj_value': row.at['from']/row.at['to'],
                    'adj_type': 'mul',
                    'date_col': timestamp,
                    'cols': ['open', 'high', 'low', 'close']
                }
                temp = apply_adjustment(temp, **params)
                params.update({
                    'adj_value': row.at['to'] / row.at['from'],
                    'cols': ['volume']
                    })
                temp = apply_adjustment(temp, **params)
                cols = ['open', 'high', 'low', 'close', 'volume']
                temp.index = df.loc[df[symbol] == row.at[symbol]].index  
                df.loc[temp.index] = temp
            df.to_hdf(self.engine, key='/data/'+self.tablename, format='table',
                        data_columns=True)


def collate_data(directory, function=None, **kwargs):
    """
    Given a directory of csv files with similar structure,
    create a dataframe by concantenating all files
    directory
        directory with the files. All files should
        be of the same structure and there should
        be no sub-directory inside it
    function
        function to be run on each file
        By default, pandas read_csv function is
        run on each file. If you specify your own
        function, it should have only filename
        as its argument and must return a dataframe
    kwargs
        kwargs for the pandas read_csv function
    """
    collect = []
    for root, directory, files in os.walk(directory):
        for file in files:
            filename = os.path.join(root, file)
            if function is None:
                temp = pd.read_csv(filename, **kwargs)
            else:
                temp = function(filename)
            collect.append(temp)
    result = pd.concat(collect).reset_index(drop=True)
    return result