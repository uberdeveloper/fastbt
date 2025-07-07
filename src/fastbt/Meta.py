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
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    Type,
    DefaultDict,
    NamedTuple,
)

# Define a TypeVar for functions that can be decorated by pre/post
F = TypeVar("F", bound=Callable[..., Any])
# Define a TypeVar for 'self' in pre/post, expecting get_override and rename methods
T = TypeVar("T", bound="Broker")  # Assuming Broker or similar interface for these methods


class Status(Enum):
    COMPLETE = 1
    PENDING = 2
    PARTIAL = 3
    REJECTED = 4
    CANCELED = 5


def pre(func: F) -> F:
    name = func.__name__

    def f(*args: Any, **kwargs: Any) -> Any:
        # Assuming the first argument is 'self' which has get_override and rename
        self_obj: Any = args[0]
        override: Optional[Dict[str, str]] = self_obj.get_override(name)
        if override:
            kwargs = self_obj.rename(kwargs, override)
        return func(*args, **kwargs)

    return f  # type: ignore # Decorator typing can be complex


def post(func: F) -> F:
    name = func.__name__

    def f(*args: Any, **kwargs: Any) -> Any:
        self_obj: Any = args[0]
        override: Optional[Dict[str, str]] = self_obj.get_override(name)
        response: Any = func(*args, **kwargs)
        if override:
            if isinstance(response, list):
                return [self_obj.rename(r, override) for r in response if isinstance(r, dict)]
            elif isinstance(response, dict):
                return self_obj.rename(response, override)
        return response

    return f  # type: ignore # Decorator typing can be complex


class TradingSystem:
    def __init__(self, auth: Any = None, tradebook: Optional[TradeBook] = None) -> None:
        """
        Initialize the system
        """
        self.auth: Any = auth
        self._cycle: int = 0
        self._data: List[Any] = []  # Define more specific type if possible
        # Pipeline is a list of 2-tuples with function
        # name being the first element, and kwargs the second element
        self._pipeline: List[Tuple[str, Dict[str, Any]]] = [
            ("dummy", {}),
            ("fetch", {}),
            ("process", {}),
            ("entry", {}),
            ("exit", {}),
            ("order", {}),
        ]
        if tradebook is None:
            self.tb: TradeBook = TradeBook(name="TradingSystem")
        else:
            self.tb = tradebook
        # List of options for the system
        self._options: Dict[str, Union[int, float]] = {
            "max_positions": 20,
            "cycle": 1e6,
        }

    @property
    def options(self) -> Dict[str, Union[int, float]]:
        return self._options.copy()

    @property
    def data(self) -> List[Any]:
        return self._data.copy()

    @property
    def cycle(self) -> int:
        return self._cycle

    @property
    def pipeline(self) -> List[Tuple[str, Dict[str, Any]]]:
        return self._pipeline

    def fetch(self) -> None:
        """
        Data fetcher.
        Use this method to fetch data
        """
        pass

    def process(self) -> None:
        """
        preprocess data before storing it
        This method should update the data property
        for further processing
        """
        pass

    def entry(self) -> None:
        """
        Entry conditions checking must go here
        """
        pass

    def exit(self) -> None:
        """
        Exit conditions checking must go here
        """
        pass

    def order(self) -> None:
        """
        Order placement should go here and adjust tradebook
        """
        pass

    def add_to_pipeline(
        self, method: str, position: Optional[int] = None, **kwargs: Any
    ) -> None:
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
        if position is None: # Check for None explicitly
            position = len(self._pipeline)
        if getattr(self, method, None) is not None:
            self._pipeline.insert(position, (method, kwargs))

    def run(self) -> None:
        """
        This should be the only method to call at a high level.
        This method calls every method in the pipeline
        Must update the cycle after run

        Note:
        zero th index is discarded in the pipeline since its empty
        """
        for method, fkwargs in self._pipeline:
            # Returns None if method not found
            func_to_call = getattr(self, method, lambda **k: None) # Ensure kwargs are accepted
            func_to_call(**fkwargs)
        self._cycle += 1


class ExtTradingSystem(TradingSystem):
    """
    An extended trading system with a few bells
    and whistles to make things simpler

    All functions beginning with **is** are Boolean functions.
    They return either True or False and used to check for
    some condition
    """

    def __init__(
        self, name: str = "trading_system", symbol: Optional[str] = None, **kwargs: Any
    ) -> None:
        # Default arguments and values
        date_str: str = datetime.datetime.today().strftime("%Y-%m-%d")
        # namedtuple("Time", "hour,minute") # This line doesn't seem to be used
        self.date: str = date_str
        self.log: Dict[Any, Any] = {} # Define more specific type if possible
        self._symbol: Optional[str] = symbol
        self._timestamp: datetime.datetime = datetime.datetime.now()
        self.name: str = name
        # Attributes that will be set by kwargs or defaults
        self.MAX_GLOBAL_POSITIONS: int
        self.MAX_QTY: int
        default_args: Dict[str, int] = {
            "MAX_GLOBAL_POSITIONS": 1,  # maximum global positions
            "MAX_QTY": 100,  # maximum open quantity per stock
        }
        for k, v in default_args.items():
            if k in kwargs:
                setattr(self, k, kwargs.pop(k))
            else:
                setattr(self, k, v)
        super(ExtTradingSystem, self).__init__(**kwargs) # Pass remaining kwargs

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def isEntry(self) -> bool:
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
        # Assuming tb.positions is Dict[Optional[str], Union[int, float]]
        current_pos: Union[int, float] = self.tb.positions.get(self._symbol, 0)
        if abs(current_pos) >= self.MAX_QTY:
            return False
        else:
            return True

    def add_trade(self, string: str, **kwargs: Any) -> None:
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
        dct: Dict[str, Any] = {
            "timestamp": self._timestamp,
            "symbol": self._symbol,
            "qty": 1,
        }
        dct.update(**kwargs)
        order_type: str = string[0]
        price: float = float(string[1:])
        dct.update({"price": price, "order": order_type})
        self.tb.add_trade(**dct)

    def run(self) -> None:
        """
        run function overriden
        """
        for method, fkwargs in self._pipeline:
            if method == "entry":
                if self.isEntry:
                    self.entry(**fkwargs)
            else:
                func_to_call = getattr(self, method, lambda **k: None)
                func_to_call(**fkwargs)
        self._cycle += 1


class CandleStickSystem(TradingSystem):
    """
    A basic candlestick trading system
    """

    def __init__(
        self,
        pattern: Any = None,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        symbol: str = "symbol",
        **kwargs: Any, # Added to catch auth/tradebook from super
    ) -> None:
        print("Hello world")
        self.pattern: Any = pattern # Define more specific type if possible
        self.entry_price: Optional[float] = entry_price
        self.exit_price: Optional[float] = exit_price
        self.signal: Optional[str] = None  # to be one of LONG/SHORT/None
        self.symbol: str = symbol
        self.c: Counter[Any] = Counter()
        self.MAX_TRADES: int = 2
        # self._cycle = 0 # Already initialized in TradingSystem
        self.timestamp: Optional[datetime.datetime] = None # Or datetime.datetime
        super(CandleStickSystem, self).__init__(**kwargs)


    def add_trade(self, **kwargs: Any) -> None:
        """
        Enter into a trade
        kwargs
            kwargs for the tradebook
        """
        defaults: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "symbol": self.symbol,
            "price": 0,
            "qty": 1,
            "order": "B", # Default order type
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

    def __init__(self, **kwargs: Any) -> None:
        """
        All initial conditions go here
        kwargs
        The following keyword arguments are supported
        is_override
            use the override option
        override_file
            path to override file
        """
        self._sides: Dict[str, str] = {"B": "S", "S": "B"}
        self._override: Dict[str, Dict[str, str]] = {
            "orders": {},
            "positions": {},
            "trades": {},
            "profile": {},
            "quote": {},
            "order_place": {},
            "order_cancel": {},
            "order_modify": {},
        }
        kwargs.pop("is_override", True) # is_override is used to enable/disable reading override file
        # Determine file_path for the derived class, not Broker itself
        actual_class: Type[Broker] = self.__class__
        file_path_str: str = inspect.getfile(actual_class)
        # Ensure it's a .py file path before slicing
        if file_path_str.endswith(".py"):
             file_path_base = file_path_str[:-3]
        else: # Fallback or error handling if not a .py file (e.g. interactive)
             file_path_base = file_path_str

        override_file: str = kwargs.pop(
            "override_file", f"{file_path_base}.yaml"
        )
        try:
            with open(override_file, "r") as f:
                dct: Dict[str, Dict[str, str]] = yaml.safe_load(f)
            if dct: # Check if dct is not None
                for k, v in dct.items():
                    self.set_override(k, v)
        except FileNotFoundError:
            print(f"Default override file not found: {override_file}")
        except yaml.YAMLError:
            print(f"Error parsing YAML file: {override_file}")


    def get_override(self, key: Optional[str] = None) -> Union[Dict[str, str], Dict[str, Dict[str, str]]]:
        """
        get the override for the given key
        returns all if key is not specified
        Note
        ----
        key should be implemented as a method
        """
        if key:
            return self._override.get(key, {})
        return self._override.copy()

    def set_override(self, key: str, values: Dict[str, str]) -> Dict[str, str]:
        """
        set the overrides for the given key
        key
            key - usually a method
        values
            values for the key
        returns the key if added
        """
        self._override[key] = values
        return self.get_override(key) # type: ignore # get_override can return more

    def authenticate(self) -> Any:
        """
        Authenticate the user usually via an interface.
        This methods takes no arguments. Any arguments
        should be passed in the __init__ method
        """
        raise NotImplementedError

    def profile(self) -> Any: # Define more specific return type in subclasses
        """
        Return the user profile
        """
        raise NotImplementedError

    def orders(self) -> List[Dict[str, Any]]:
        """
        Get the list of orders
        """
        raise NotImplementedError

    def trades(self) -> List[Dict[str, Any]]:
        """
        Get the list of trades
        """
        raise NotImplementedError

    def positions(self) -> List[Dict[str, Any]]:
        """
        Get the list of positions
        """
        raise NotImplementedError

    def order_place(self, **kwargs: Any) -> Any: # Define more specific return type
        """
        Place an order
        """
        raise NotImplementedError

    def order_modify(self, order_id: Any, **kwargs: Any) -> Any: # Define specific type for order_id
        """
        Modify an order with the given order id
        """
        raise NotImplementedError

    def order_cancel(self, order_id: Any, **kwargs: Any) -> Any: # Define specific type for order_id
        """
        Cancel an order with the given order id
        """
        raise NotImplementedError

    def quote(self, symbol: str, **kwargs: Any) -> Any: # Define more specific return type
        """
        Get the quote for the given symbol
        """
        raise NotImplementedError

    @staticmethod
    def dict_filter(lst: List[Dict[str, Any]], **kwargs: Any) -> List[Dict[str, Any]]:
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
        if not lst: # Simpler check for empty list
            # print("Nothing in the list") # This print can be noisy, consider removing or logging
            return []
        new_lst: List[Dict[str, Any]] = []
        for d_item in lst: # Renamed 'd' to 'd_item' to avoid conflict if 'd' is a kwarg key
            case: bool = True
            for k, v in kwargs.items():
                if d_item.get(k) != v:
                    case = False
                    break # Optimization: no need to check further if one condition fails
            if case:
                new_lst.append(d_item)
        return new_lst

    @staticmethod
    def rename(dct: Dict[str, Any], keys: Dict[str, str]) -> Dict[str, Any]:
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
        >>> Broker.rename({'a': 10, 'b':20}, {'a': 'aa'})
        {'aa': 10, 'b': 20}
        >>> Broker.rename({'a': 10, 'b': 20}, {'c': 'm'})
        {'a': 10, 'b': 20}
        """
        new_dct: Dict[str, Any] = {}
        for k, v in dct.items():
            if k in keys: # More direct check
                new_dct[keys[k]] = v
            else:
                new_dct[k] = v
        return new_dct

    def cancel_all_orders(self, **kwargs: Any) -> None:
        """
        Cancel all pending orders.
        To close a particular class or orders, include
        them in kwargs
        """
        # Assuming self.orders() returns List[Dict[str, Any]]
        # and order_id is present in each dict
        current_orders: List[Dict[str, Any]] = self.orders()
        if kwargs:
            # Assuming `at` was a typo for `self` or a missing import `fastbt.utils`
            # For now, assuming it's self.dict_filter
            current_orders = self.dict_filter(current_orders, **kwargs)
        if len(current_orders) > 0: # Check filtered orders
            for order in current_orders: # Iterate through filtered orders
                if "order_id" in order:
                    self.order_cancel(order["order_id"])
                # else: log or handle missing order_id

    def close_all_positions(self, **kwargs: Any) -> None:
        """
        Close all existing positions by placing
        market orders.
        To close a particular class of orders, include
        them in kwargs
        """
        current_positions: List[Dict[str, Any]] = self.positions()
        if kwargs:
            current_positions = self.dict_filter(current_positions, **kwargs)

        if len(current_positions) > 0:
            for position in current_positions:
                qty: Union[int, float] = abs(position.get("quantity", 0))
                symbol: Optional[str] = position.get("symbol")
                # Assuming position side is 'B' or 'S'. If not, this will fail.
                original_side: Optional[str] = position.get("side")

                if qty > 0 and symbol and original_side and original_side in self._sides:
                    closing_side: str = self._sides[original_side]
                    self.order_place(
                        symbol=symbol, quantity=qty, order_type="MARKET", side=closing_side
                    )
                # else: log or handle missing keys or invalid side

    def consolidated(self, **kwargs: Any) -> DefaultDict[str, Counter[Any]]:
        """
        Get the consolidated list of orders and positions
        by each symbol
        """
        dct: DefaultDict[str, Counter[Any]] = defaultdict(Counter)
        ords: List[Dict[str, Any]] = self.orders()
        # Assuming `at` was a typo for `self` or a missing import `fastbt.utils`
        # For now, assuming it's self.dict_filter
        ords = self.dict_filter(ords, **kwargs)

        pending_orders: List[Dict[str, Any]] = []
        for o in ords:
            status = o.get("status")
            if (status == "PENDING") or (status == "PARTIAL"):
                pending_orders.append(o)

        for o in pending_orders:
            symbol: Optional[str] = o.get("symbol")
            if not symbol: continue # Skip if no symbol

            price: float = max(o.get("price", 0.0), o.get("trigger_price", 0.0))
            quantity: float = o.get("quantity", 0.0)
            filled_quantity: float = o.get("filled_quantity", 0.0)
            side: Optional[str] = o.get("side")
            if side is None: continue # Skip if no side

            qty_to_consider: float = abs(quantity) - abs(filled_quantity)
            value: float = abs(price * qty_to_consider)

            dct[symbol][side] += qty_to_consider
            text: str = f"{side}_value"
            dct[symbol][text] += value # Use += for Counter update consistency

        current_positions: List[Dict[str, Any]] = self.positions()
        current_positions = self.dict_filter(current_positions, **kwargs)

        for p in current_positions:
            symbol = p.get("symbol")
            if not symbol: continue

            price = p.get("average_price", 0.0)
            quantity = p.get("quantity", 0.0)
            side = p.get("side")
            if side is None: continue

            value = abs(price * quantity)
            text = f"{side}_value"
            dct[symbol][side] += abs(quantity)
            dct[symbol][text] += value
        return dct

    def not_covered(
        self, tick_size: float = 0.05, **kwargs: Any
    ) -> List[NamedTuple]: # More specific NamedTuple if defined
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
        all_orders: DefaultDict[str, Counter[Any]] = self.consolidated(**kwargs)
        UncoveredTuple = namedtuple( # type: ignore
            "uncovered", ["symbol", "side", "quantity", "price"]
        )
        uncovered_list: List[NamedTuple] = [] # Use the specific namedtuple type

        for k, v_counter in all_orders.items(): # k is symbol, v_counter is the Counter
            buy_qty: float = v_counter.get("BUY", 0.0)
            sell_qty: float = v_counter.get("SELL", 0.0)
            buy_value: float = v_counter.get("BUY_value", 0.0)
            sell_value: float = v_counter.get("SELL_value", 0.0)

            if buy_qty > sell_qty:
                avg_price: float = tick(buy_value / buy_qty if buy_qty else 0, tick_size)
                tp = UncoveredTuple(k, "SELL", buy_qty - sell_qty, avg_price)
                uncovered_list.append(tp)
            elif sell_qty > buy_qty:
                avg_price = tick(sell_value / sell_qty if sell_qty else 0, tick_size)
                tp = UncoveredTuple(k, "BUY", sell_qty - buy_qty, avg_price)
                uncovered_list.append(tp)
        return uncovered_list

    def _create_stop_loss_orders(
        self, percent: Union[int, float] = 1, tick_size: float = 0.05, **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Create a list of stop orders for orders not covered
        percent
            percentage of stop loss on the average price
        """
        not_covered_list: List[NamedTuple] = self.not_covered(tick_size=tick_size, **kwargs)
        lst: List[Dict[str, Any]] = []

        def get_sl(price: float, side: str, stop_percent: Union[int, float]) -> float:
            """
            Get stop loss for the order
            Note
            -----
            The implementation is in the reverse since we
            already knew the side to place the order and
            the price is that of the opposite side
            """
            if side == "BUY": # Need to buy to cover short, so SL is higher
                return tick(price * (1 + stop_percent * 0.01), tick_size)
            elif side == "SELL": # Need to sell to cover long, so SL is lower
                return tick(price * (1 - stop_percent * 0.01), tick_size)
            else: # Should not happen with current logic of not_covered
                return price

        for nc in not_covered_list:
            dct: Dict[str, Any] = {}
            # Assuming nc is the NamedTuple("uncovered", ["symbol", "side", "quantity", "price"])
            dct["symbol"] = nc.symbol     # type: ignore
            dct["quantity"] = nc.quantity # type: ignore
            dct["side"] = nc.side         # type: ignore
            dct["price"] = get_sl(nc.price, nc.side, percent) # type: ignore
            lst.append(dct)
        return lst
