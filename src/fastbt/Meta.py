"""
This is the meta trading class from which other classes
are derived
"""
from fastbt.tradebook import TradeBook
from collections import namedtuple, Counter
from inspect import isfunction
import datetime
import os

class TradingSystem:

    def __init__(self, auth=None, tradebook=None):
        """
        Initialize the system
        """
        self.auth = auth
        self._cycle = 0
        self._data = []
        # Pipeline is a list of 3-tuples with function
        # name being the first element, args the 
        # second element and kwargs the third element
        self._pipeline = [
            ('dummy', {}),
            ('fetch',  {}),
            ('process', {}),
            ('entry', {}),
            ('exit', {}),
            ('order', {})
        ]
        if tradebook is None:
            self.tb = TradeBook(name="TradingSystem")
        else:
            self.tb = tradebook
        # List of options for the system
        self._options = {
            'max_positions': 20,
            'cycle': 1e6
        }       

    @property
    def options(self):
        return self._options.copy()

    @property
    def data(self):
        return self._data.copy()

    @property
    def cycle(self):
        return self._cycle

    @property
    def pipeline(self):
        return self._pipeline   

    def fetch(self):
        """
        Data fetcher.
        Use this method to fetch data
        """
        pass

    def process(self):
        """
        preprocess data before storing it
        This method should update the data property
        for further processing
        """
        pass

    def entry(self):
        """
        Entry conditions checking must go here
        """
        pass

    def exit(self):
        """
        Exit conditions checking must go here
        """
        pass

    def order(self):
        """
        Order placement should go here and adjust tradebook
        """
        pass

    def add_to_pipeline(self, method, position=None, **kwargs):
        """
        Add a method to the existing pipeline
        method
            method to be added; should be part of the object
        position
            position of this method in the pipeline.
            Pipeline starts at 1 (0 is used for initialization).
            So to insert an item at the second positions, use 2.
        kwargs
            keyword arguments to the function
        Note
        -----
        Internally, the pipeline is represented by a list
        and the position argument is a call to the 
        insert method of the list object
        """
        if not(position):
            position = len(self._pipeline)
        if getattr(self, method, None):
            self._pipeline.insert(position, (method, kwargs))

    def run(self):
        """
        This should be the only method to call at a high level. 
        This method calls every method in the pipeline
        Must update the cycle after run

        Note:
        zero th index is discarded in the pipeline since its empty
        """
        for method, fkwargs in self._pipeline:
            # Returns None if method not found          
            getattr(self, method, lambda : None)(**fkwargs)
            # Check whether the function is given any 
            # positional or keyword arguments
            """
            isArgs = len(fargs) > 0
            isKwargs = len(fkwargs) > 0
            if isArgs and isKwargs:
                func(*fargs, **fkwargs)
            elif isArgs:
                func(*fargs)
            elif isKwargs:
                func(**fkwargs)
            else:
                func()
            """
        self._cycle += 1


class ExtTradingSystem(TradingSystem):
    """
    An extended trading system with a few bells
    and whistles to make things simpler

    All functions beginning with **is** are Boolean functions.
    They return either True or False and used to check for
    some condition
    """
    def __init__(self, name='trading_system', **kwargs):
        # Default arguments and values
        date = datetime.datetime.today().strftime('%Y-%m-%d')
        Time = namedtuple('Time', 'hour,minute')
        self.date = date
        self.log = {}
        self._timestamp = datetime.datetime.now()
        # TO DO: Apply some logic
        self.name = name

        args = {
            'MAX_TRADES': 2, # Maximum trades per symbol
            'MAX_GLOBAL_TRADES': 10, # Global maximum trades
            'MAX_GLOBAL_POSITIONS': 1, # Only one position could be held
            'MAX_VALUE': 1e10, # Max value per stock
            'save_file': os.path.join(os.curdir, self.name+'.msg'),            
            'restoreData': True,
            # A named tuple for entry and exit times
            'enterBefore': Time(hour=15, minute=0), # Don't enter into positions after this time
            'enterAfter': Time(hour=9, minute=15), # Enter into positions after this time
            'exitAfter': Time(hour=0, minute=0), # Only check for exits after this time
            'exitTime': Time(hour=15, minute=10), # Exit all positions at this time
        }
        for k,v in args.items():
            if k in ['enterBefore', 'exitTime']:
                if k in kwargs:
                    setattr(self, k, Time(*kwargs.pop(k)))
                else:
                    setattr(self, k, v)
            else:
                setattr(self, k, kwargs.pop(k, v))
        super(ExtTradingSystem, self).__init__()

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def isGlobalPositions(self):
        """
        is Max Global positions hit
        """
        pass

    def isMaxTrades(self, symbol):
        pass

    def isMaxValue(self, symbol):
        pass

    def isMaxPercent(self, symbol):
        pass


    def isEntry(self):
        """
        Check whether we could enter into a position
        """
        pass


class CandleStickSystem(TradingSystem):
    """
    A basic candlestick trading system
    """
    def __init__(self, pattern=None, entry_price=None,
        exit_price=None, symbol='symbol'):
        print('Hello world')
        self.pattern = pattern
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.signal = None # to be one of LONG/SHORT/None
        self.symbol = symbol
        self.c = Counter()
        self.MAX_TRADES = 2
        self._cycle = 0
        self.timestamp = None
        super(CandleStickSystem, self).__init__()

    def add_trade(self, **kwargs):
        """
        Enter into a trade
        kwargs
            kwargs for the tradebook
        """
        defaults = {
            'timestamp': self.timestamp,
            'symbol': self.symbol,
            'price': 0,
            'qty': 1,
            'order': 'B',
            'cycle': self.cycle
        }
        defaults.update(**kwargs)
        self.tb.add_trade(**defaults)


    

