"""
DataStore object with common functions
This is intended as a shortcut for otherwise
more verbose functions

Requirements
1) Input type should be a pandas dataframe
2) Input should have both symbol and timestamp columns
3) Indexes are reset and existing index dropped. So, if symbol or
   timestamp is in the index, convert them into columns  
4) All columns are renamed to lower case
"""

class DataSource(object):
    def __init__(self, data, symbol=None, timestamp=None, sort=True):
        """
        Initialize the dataframe
        By default, all columns would be converted into lower case, 
        values would be sorted by timestamp and indexes would be reset
        symbol
            symbol column
        timestamp
            timestamp column
        sort
            whether to sort data by timestamp
            if data is already sorted, pass False to save time
        """
        import hashlib
        self.hash = hashlib.sha1().hexdigest()
        self._isTALIB = True
        data = data.rename({symbol: 'symbol', timestamp: 'timestamp'},
            axis='columns')
        data = data.rename(str.lower, axis='columns')
        if sort:
            self._data = data.sort_values(by='timestamp').reset_index(drop=True)
        else:
            self._data = data.reset_index(drop=True)

        try:
            import talib
            self._func_map = {
                'BBANDS': (talib.BBANDS, ['close']),
                'DEMA': (talib.DEMA, ['close']),
                'EMA': (talib.EMA, ['close']),
                'KAMA': (talib.KAMA, ['close']),
                'MA': (talib.MA, ['close']),
                'MAMA': (talib.MAMA, ['close']),
                'MIDPOINT': (talib.MIDPOINT, ['close']),
                'MIDPRICE': (talib.MIDPRICE, ['high', 'low']),
                'SAR': (talib.SAR, ['high', 'low']),
                'SAREXT': (talib.SAREXT, ['high', 'low']),
                'SMA': (talib.SMA, ['close']),
                'STDDEV': (talib.STDDEV, ['close']),
                'TEMA': (talib.TEMA, ['close']),
                'TRIMA': (talib.TRIMA, ['close']),
                'WMA': (talib.WMA, ['close']),
                'AD': (talib.AD, ['high', 'low', 'close', 'volume']),
                'OBV': (talib.OBV, ['close', 'volume']),
                'ATR': (talib.ATR, ['high', 'low', 'close']),
                'NATR': (talib.NATR, ['high', 'low', 'close']),
                'TRANGE': (talib.TRANGE, ['high', 'low', 'close']),
                'ADX': (talib.ADX, ['high', 'low', 'close']),
                'AROON': (talib.AROON, ['high', 'low']),
                'BOP': (talib.BOP, ['open', 'high', 'low', 'close']),
                'CCI': (talib.CCI, ['high', 'low', 'close']),
                'DX': (talib.DX, ['high', 'low', 'close']),
                'MACD': (talib.MACD, ['close']),
                'MOM': (talib.MOM, ['close']),
                'ROC': (talib.ROC, ['close']),
                'RSI': (talib.RSI, ['close']),
                'STOCH': (talib.STOCH, ['high', 'low', 'close']),
                'STOCHF': (talib.STOCHF, ['high', 'low', 'close']),
                'STOCHRSI': (talib.STOCHRSI, ['close']),
                'ULTOSC': (talib.ULTOSC, ['high', 'low', 'close']),
                'WILLR': (talib.WILLR, ['high', 'low', 'close'])
            }
        except ModuleNotFoundError:
            self._isTALIB = False
            print('TALIB not installed')

    @property
    def data(self):
        return self._data

    def add_lag(self, on='close', period=1, col_name='auto'):
        """
        add lagged data based on symbol
        on
            column on which lag is to be added
        period
            period of lagging
        col_name
            column name
            By default, column name is created as lag_{{column}}_{{period}}
        """
        grouped = self.data.groupby('symbol')
        if col_name == 'auto':
            col_name = 'lag_' + on + '_' + str(period)
        col = grouped[on].transform(lambda x: x.shift(period))
        self._data[col_name.lower()] = col
        return self.data

    def add_pct_change(self, on='close', period=1, col_name='auto',
                        lag=None, **kwargs):
        """
        Add percentage change based on symbol
        lag
            also add lag by one period
        """
        grouped = self.data.groupby('symbol')
        if col_name == 'auto':
            col_name = 'chg_' + on + '_'+ str(period)
        col = grouped[on].transform(lambda x: x.pct_change(period, **kwargs))
        if lag:
            self._data[col_name + self.hash] = col
            self.add_lag(on=col_name+self.hash, period=lag, col_name=col_name)
            del self._data[col_name + self.hash]
        else:
            self._data[col_name.lower()] = col
        return self.data

    def add_rolling(self, window, groupby='symbol', on='close', 
                    function='mean', col_name='auto',lag=None, **kwargs):
        """
        Add rolling window statistics
        This is just a wrapper for the pandas rolling functions
        window
            rolling period window
        groupby
            column to group data by
        on
            column on which the rolling window is to be applied
        function
            function to be applied for the rolling window as
            a string. All pandas rolling window functions are
            accepted
        col_name
            column_name
        lag
            shift the data
        kwargs
            kwargs for the pandas window function
        This is just a wrapper for
        >>> df.groupby(groupby)[on].transform(lambda x: x.rolling(**kwargs).agg(function))
        """
        grouped = self.data.groupby(groupby)
        if col_name == 'auto':
            col_name = 'rol_{f}_{on}_{w}'.format(f=function, on=on, w=window)
        col = grouped[on].transform(lambda x: x.rolling(window, **kwargs).agg(function))
        if lag:
            self._data[col_name + self.hash] = col
            self.add_lag(on=col_name+self.hash, period=lag, col_name=col_name)
            del self._data[col_name + self.hash]
        else:
            self._data[col_name.lower()] = col
        return self.data
        
    def add_formula(self, formula, col_name):
        """
        Add a formula to the dataframe
        Formulas are simple one-line expressions
            see numexpr expressions for more details
        formula
            formula as a string
        col_name
            column name to use
        Note
        -----
        Formula string is renamed to lower case.
        So, formula, FORMULA, Formula are all equivalent
        """
        self._data[col_name.lower()] = self._data.eval(formula.lower())
        return self.data

    def add_indicator(self, indicator, period=None, col_name='auto', 
                    lag=None, **kwargs):
        """
        Add an indicator
        indicator
            indicator name as a string - case insensitive
        period
            the timeperiod argument for talib library
        col_name
            column name for this indicator
        kwargs for the indicator
        """
        if not(self._isTALIB):
            return 'TALIB not installed'
        indicator = indicator.upper()
        if period is not None:
            kwargs.update({'timeperiod': period})
        func, args = self._func_map.get(indicator, (None, None))

        if func is None:            
            raise NameError('Function not available\n' + 
             'Only the following functions are available\n{}'.format(self._func_map.keys()))

        def apply_func(group):
            cols = [group[arg] for arg in args]
            return func(*cols, **kwargs)

        data = self.data.reset_index(drop=True)
        grouped = data.groupby('symbol')
        result = grouped.apply(apply_func).reset_index(level='symbol')
        if col_name == 'auto':
            col_name = indicator + '_' + str(period if period is not None else 0)
        del result['symbol'] # Removed for easy join
        if lag:
            result.columns = [col_name + self.hash]
            self._data = data.join(result)
            self.add_lag(on=col_name+self.hash, period=lag, col_name=col_name)
            del self._data[col_name + self.hash]
        else:
            result.columns = [col_name.lower()]
            self._data = data.join(result)
        return self.data

    def batch_process(self, batch):
        """
        Process data in batch
        batch
            list of key,value pairs as arguments
            with key name being the code and
            value being a dictionary of arguments
            to the function

        code
        -----
        L - lag
        P - percent change
        F - formula
        I - indicator 
        """
        f_map = {
        'L': self.add_lag,
        'P': self.add_pct_change,
        'F': self.add_formula,
        'I': self.add_indicator,
        'R': self.add_rolling
        }

        for item in batch:
            # Parse data arguments and return final data
            k,v = tuple(item.items())[0]
            func = f_map[k]
            self._data = func(**v)        
        return self.data