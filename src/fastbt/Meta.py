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
        self.name = name
        default_args = {
            'MAX_GLOBAL_POSITIONS': 1, # maximum global positions
            'MAX_QTY': 100 # maximum open quantity per stock
        }
        for k,v in default_args.items():
            if k in kwargs:
                setattr(self, k, kwargs.pop(k))
            else:
                setattr(self, k, v)
        super(ExtTradingSystem, self).__init__()

    @property
    def timestamp(self):
        return self._timestamp

    @property    
    def isEntry(self):
        """
        conditions to check before entering into a position.
        returns True/False
        position is entered only when this is True
        Note
        -----
        Put all conditions to check before entering into a 
        position here.
        """
        # List of conditions to check
        if self.tb.o >= self.MAX_GLOBAL_POSITIONS:
            return False
        elif abs(self.tb.positions.get(self._symbol, self.MAX_QTY)) >= self.MAX_QTY:
            return False
        else:
            return True

    def run(self):
        """
        run function overriden
        """
        for method, fkwargs in self._pipeline:
            # Returns None if method not found 
            if method == 'entry':
                if self.isEntry:
                    self.entry(**fkwargs)
            else:
                getattr(self, method, lambda : None)(**fkwargs)
        self._cycle += 1




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


    

