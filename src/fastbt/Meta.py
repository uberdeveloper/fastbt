"""
This is the meta trading class from which other classes
are derived
"""
from fastbt.tradebook import TradeBook
from fastbt.utils import tick
from collections import namedtuple, Counter, defaultdict
from enum import Enum
import inspect
import datetime
import yaml


class Status(Enum):
    COMPLETE = 1
    PENDING = 2
    PARTIAL = 3
    REJECTED = 4
    CANCELED = 5


def pre(func):
    name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        if override:
            kwargs = self.rename(kwargs, override)
        return func(*args, **kwargs)

    return f


def post(func):
    name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        response = func(*args, **kwargs)
        if override:
            if isinstance(response, list):
                return [self.rename(r, override) for r in response]
            elif isinstance(response, dict):
                return self.rename(response, override)
        return response

    return f


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
            ("dummy", {}),
            ("fetch", {}),
            ("process", {}),
            ("entry", {}),
            ("exit", {}),
            ("order", {}),
        ]
        if tradebook is None:
            self.tb = TradeBook(name="TradingSystem")
        else:
            self.tb = tradebook
        # List of options for the system
        self._options = {"max_positions": 20, "cycle": 1e6}

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
        if not (position):
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
            getattr(self, method, lambda: None)(**fkwargs)
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

    def __init__(self, name="trading_system", symbol=None, **kwargs):
        # Default arguments and values
        date = datetime.datetime.today().strftime("%Y-%m-%d")
        namedtuple("Time", "hour,minute")
        self.date = date
        self.log = {}
        self._symbol = symbol
        self._timestamp = datetime.datetime.now()
        self.name = name
        default_args = {
            "MAX_GLOBAL_POSITIONS": 1,  # maximum global positions
            "MAX_QTY": 100,  # maximum open quantity per stock
        }
        for k, v in default_args.items():
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
        elif abs(self.tb.positions.get(self._symbol, 0)) >= self.MAX_QTY:
            return False
        else:
            return True

    def add_trade(self, string, **kwargs):
        """
        A simple shortcut to add trade
        string
            string with the first letter indicating B/S
            and the rest price
            (Eg)
            B130.4 = buy at price 130.4
            S77 = sell at price 77
        Note
        -----
        Even if price and order are provided in keyword
        arguments, they are overridden by the string argument
        """
        dct = {"timestamp": self._timestamp, "symbol": self._symbol, "qty": 1}
        dct.update(**kwargs)
        order, price = string[0], float(string[1:])
        dct.update({"price": price, "order": order})
        self.tb.add_trade(**dct)

    def run(self):
        """
        run function overriden
        """
        for method, fkwargs in self._pipeline:
            # Returns None if method not found
            if method == "entry":
                if self.isEntry:
                    self.entry(**fkwargs)
            else:
                getattr(self, method, lambda: None)(**fkwargs)
        self._cycle += 1


class CandleStickSystem(TradingSystem):
    """
    A basic candlestick trading system
    """

    def __init__(
        self, pattern=None, entry_price=None, exit_price=None, symbol="symbol"
    ):
        print("Hello world")
        self.pattern = pattern
        self.entry_price = entry_price
        self.exit_price = exit_price
        self.signal = None  # to be one of LONG/SHORT/None
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
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "price": 0,
            "qty": 1,
            "order": "B",
            "cycle": self.cycle,
        }
        defaults.update(**kwargs)
        self.tb.add_trade(**defaults)


class Broker:
    """
    A metaclass implementation for live trading
    All the methods need to be overriden for
    specific brokers
    Override is a mechanism through which you could
    replace the keys of the request/response to
    match the keys of the API.
    """

    def __init__(self, **kwargs):
        """
        All initial conditions go here
        kwargs
        The following keyword arguments are supported
        is_override
            use the override option
        override_file
            path to override file
        """
        self._sides = {"B": "S", "S": "B"}
        self._override = {
            "orders": {},
            "positions": {},
            "trades": {},
            "profile": {},
            "quote": {},
            "order_place": {},
            "order_cancel": {},
            "order_modify": {},
        }
        kwargs.pop("is_override", True)
        file_path = inspect.getfile(self.__class__)[:-3]
        override_file = kwargs.pop("override_file", f"{file_path}.yaml")
        try:
            with open(override_file, "r") as f:
                dct = yaml.safe_load(f)
            for k, v in dct.items():
                self.set_override(k, v)
        except FileNotFoundError:
            print("Default override file not found")

    def get_override(self, key=None):
        """
        get the override for the given ky
        returns all if key is not specified
        Note
        ----
        key should be implemented as a method
        """
        return self._override.get(key, self._override.copy())

    def set_override(self, key, values):
        """
        set the overrides for the given key
        key
            key - usually a method
        values
            values for the key
        returns the key if added
        """
        self._override[key] = values
        return self.get_override(key)

    def authenticate(self):
        """
        Authenticate the user usually via an interface.
        This methods takes no arguments. Any arguments
        should be passed in the __init__ method
        """
        raise NotImplementedError

    def profile(self):
        """
        Return the user profile
        """
        raise NotImplementedError

    def orders(self):
        """
        Get the list of orders
        """
        raise NotImplementedError

    def trades(self):
        """
        Get the list of trades
        """
        raise NotImplementedError

    def positions(self):
        """
        Get the list of positions
        """
        raise NotImplementedError

    def order_place(self, **kwargs):
        """
        Place an order
        """
        raise NotImplementedError

    def order_modify(self, order_id, **kwargs):
        """
        Modify an order with the given order id
        """
        raise NotImplementedError

    def order_cancel(self, order_id, **kwargs):
        """
        Cancel an order with the given order id
        """
        raise NotImplementedError

    def quote(self, symbol, **kwargs):
        """
        Get the quote for the given symbol
        """
        raise NotImplementedError

    @staticmethod
    def dict_filter(lst, **kwargs):
        """
        Filter a list of dictionary to conditions matching
        in kwargs
        lst
            list of dictionaries
        kwargs
            key values to filter; key is the dictionary key
            and value is the value to match.
            **This is an AND filter**

        Note
        -----
        For each dictionary in the list, each of the arguments
        in kwargs are matched and only those dictionaries that
        match all the conditions are returned
        """
        if len(lst) == 0:
            print("Nothing in the list")
            return []
        new_lst = []
        for d in lst:
            case = True
            for k, v in kwargs.items():
                if d.get(k) != v:
                    case = False
            if case:
                new_lst.append(d)
        return new_lst

    @staticmethod
    def rename(dct, keys):
        """
        rename the keys of an existing dictionary
        dct
            existing dictionary
        keys
            keys to be renamed as dictionary with
            key as existing key and value as value
            to be replaced
        Note
        -----
        A new dictionary is constructed with existing
        keys replaced by new ones. Values are not replaced.
        >>> rename({'a': 10, 'b':20}, {'a': 'aa'})
        {'aa':10, 'b': 20}
        >>> rename({'a': 10, 'b': 20}, {'c': 'm'})
        {'a':10, 'b':20}
        """
        new_dct = {}
        for k, v in dct.items():
            if keys.get(k):
                new_dct[keys[k]] = v
            else:
                new_dct[k] = v
        return new_dct

    def cancel_all_orders(self, **kwargs):
        """
        Cancel all pending orders.
        To close a particular class or orders, include
        them in kwargs
        """
        orders = self.orders()
        if kwargs:
            orders = at.dict_filter(orders, **kwargs)
        if len(orders) > 0:
            for order in self.orders():
                self.order_cancel(order["order_id"])

    def close_all_positions(self, **kwargs):
        """
        Close all existing positions by placing
        market orders.
        To close a particular class of orders, include
        them in kwargs
        """
        positions = self.positions()
        if kwargs:
            positions = self.dict_filter(positions, **kwargs)
        if len(positions) > 0:
            for position in positions:
                qty = abs(position["quantity"])
                symbol = position["symbol"]
                side = self._sides[position["side"]]
                if qty > 0:
                    self.order_place(
                        symbol=symbol, quantity=qty, order_type="MARKET", side=side
                    )

    def consolidated(self, **kwargs):
        """
        Get the consolidated list of orders and positions
        by each symbol
        """
        dct = defaultdict()
        ords = self.orders()
        ords = self.dict_filter(ords, **kwargs)
        orders = []
        for o in ords:
            if (o["status"] == "PENDING") or (o["status"] == "PARTIAL"):
                orders.append(o)
        for o in orders:
            symbol = o["symbol"]
            if not (dct.get(symbol)):
                dct[symbol] = Counter()
            price = max(o["price"], o["trigger_price"])
            qty = abs(o["quantity"]) - abs(o["filled_quantity"])
            value = abs(price * qty)
            dct[symbol][o["side"]] += qty
            text = "{}_value".format(o["side"])
            dct[symbol].update({text: value})
        positions = self.positions()
        positions = self.dict_filter(positions, **kwargs)
        for p in positions:
            symbol = p["symbol"]
            if not (dct.get(symbol)):
                dct[symbol] = Counter()
            price = p["average_price"]
            value = abs(price * p["quantity"])
            text = "{}_value".format(p["side"])
            dct[symbol][p["side"]] += abs(p["quantity"])
            dct[symbol].update({text: value})
        return dct

    def not_covered(self, tick_size=0.05, **kwargs):
        """
        Get the list of orders/positions not covered.
        returns a named tuple containing the symbol, the side not covered,
        quantity not covered and the average price of the side covered
        tick_size
            tick_size to be adjusted in the final price
        kwargs
            list of keyword arguments to filter orders and positions
            to be passed to the consolidated function
        Note
        -----
        1) This is a consolidated list including both positions and orders
        2) Orders are compared by quantity and not by price
        3) Bracket, OCO and other order types not covered
        """
        all_orders = self.consolidated(**kwargs)
        tup = namedtuple("uncovered", ["symbol", "side", "quantity", "price"])
        uncovered = []
        for k, v in all_orders.items():
            if v["BUY"] > v["SELL"]:
                avg_price = tick(v["BUY_value"] / v["BUY"], tick_size)
                tp = tup(k, "SELL", v["BUY"] - v["SELL"], avg_price)
                uncovered.append(tp)
            elif v["SELL"] > v["BUY"]:
                avg_price = tick(v["SELL_value"] / v["SELL"], tick_size)
                tp = tup(k, "BUY", v["SELL"] - v["BUY"], avg_price)
                uncovered.append(tp)
        return uncovered

    def _create_stop_loss_orders(self, percent=1, tick_size=0.05, **kwargs):
        """
        Create a list of stop orders for orders not covered
        percent
            percentage of stop loss on the average price
        """
        not_covered = self.not_covered(**kwargs)
        lst = []

        def get_sl(price, side, percent):
            """
            Get stop loss for the order
            Note
            -----
            The implementation is in the reverse since we
            already knew the side to place the order and
            the price is that of the opposite side
            """
            if side == "BUY":
                return tick(price * (1 + percent * 0.01), tick_size)
            elif side == "SELL":
                return tick(price * (1 - percent * 0.01), tick_size)
            else:
                return price

        for nc in not_covered:
            dct = {}
            dct["symbol"] = nc.symbol
            dct["quantity"] = nc.quantity
            dct["side"] = nc.side
            dct["price"] = get_sl(nc.price, nc.side, percent)
            lst.append(dct)
        return lst
