import pendulum
from typing import List, Tuple, Optional, Dict, Any
from fastbt.Meta import TradingSystem
from pydantic import BaseModel
from copy import deepcopy

# Declare global variables
TZ = "Asia/Kolkata"


def tuple_to_time(
    tup: Tuple[int, int, int] = (0, 0, 0), tz: str = "Asia/Kolkata"
) -> pendulum.DateTime:
    """
    Convert a 3-tuple to a pendulum datetime instance.
    The 3-tuple is considered to be hour, minute and second
    and added to today's date
    >>> dt = tuple_to_time()
    >>> assert dt == pendulum.today()

    >>> today = pendulum.today()
    >>> yr,mon,day = today.year, today.month, today.day
    >>> dt2 = tuple_to_time((3,4,5))
    >>> assert dt2 == pendulum.datetime(yr,mon,day,3,4,5,tz='Asia/Kolkata')
    """
    hour, minute, second = tup
    return pendulum.today(tz=tz).add(hours=hour, minutes=minute, seconds=second)


def tick(price: float, tick_size: float = 0.05) -> float:
    """
    round the given price to the nearest tick
    >>> tick(100.03)
    100.05
    >>> tick(101.31, 0.5)
    101.5
    >>> tick(101.04, 0.1)
    101.0
    >>> tick(100.01,0.1)
    100.0
    """
    return round(round(price / tick_size) * tick_size, 2)


def smart_buffer(price: float, side: str) -> float:
    """
    Provide a smart buffer to the given price
    price
        price to be traded
    side
        TO DO: Convert this to an Enum
        BUY or SELL
    >>> smart_buffer(43.5,'BUY')
    43.5
    >>> smart_buffer(43.5,'SELL')
    43.5
    >>> smart_buffer(91.7, 'BUY')
    91.65
    >>> smart_buffer(91.7, 'SELL')
    91.75
    >>> smart_buffer(124.65, 'BUY')
    124.55
    >>> smart_buffer(124.65, 'SELL')
    124.75
    >>> smart_buffer(587.4, 'BUY')
    587.1
    >>> smart_buffer(21246.75, 'SELL')
    21257.35
    """
    sign = -1 if side == "BUY" else 1
    if price < 50:
        return price
    elif price < 100:
        return round(price + (sign * 0.05), 2)
    elif price < 200:
        return round(price + (sign * 0.10), 2)
    else:
        return round(tick(price + (sign * price * 0.05 * 0.01)), 2)


class BaseSystem(TradingSystem):
    """
    This is an abstract system.
    Do not initialize it directly
    """

    # Declare default parameters
    _params = {
        "INTERVAL": 60,  # in seconds
        "MAX_POSITIONS": 10,
        # All parameters that end with TIME
        # take a 3-tuple with hour,minute,second as arguments
        "SYSTEM_START_TIME": (9, 15, 0),
        "SYSTEM_END_TIME": (15, 15, 0),
        "TRADE_START_TIME": (9, 16, 0),
        "TRADE_END_TIME": (15, 0, 0),
        "SQUARE_OFF_TIME": (15, 15, 0),
        "TZ": "Asia/Kolkata",
        "CAPITAL_PER_STOCK": 100000,
        "RISK_PER_STOCK": 1000,
        "WEIGHTAGE": "capital",  # either capital or risk
        # default keyword arguments to be passed to order
        "ORDER_DEFAULT_KWARGS": {},
    }

    def __init__(
        self,
        name: str = "base_strategy",
        env: str = "paper",
        broker: Any = None,
        **kwargs
    ):
        """
        Initialize the strategy.
        The initialize sets up sensible defaults
        name
            name of the strategy
        env
            environment in which it is traded.
            if env is live real trades are executed
        broker
            broker class in case of live trading
        kwargs
            list of keyword arguments to modify the system
        """
        for k, v in self._params.items():
            if k in kwargs:
                value = kwargs.get(k)
            else:
                value = v
            if k.endswith("TIME"):
                value = tuple_to_time(value)
            setattr(self, k, value)
        self._cycle = 0
        self._name = name
        self._env = env
        self._broker = broker
        self._done = False
        self._periods = self.get_time_periods()
        self.next_scan = self.get_next_scan()
        self.buffer = smart_buffer

    @property
    def name(self) -> str:
        return self._name

    @property
    def env(self) -> str:
        return self._env

    @property
    # TO DO: Properly type cast broker
    def broker(self) -> Any:
        return self._broker

    @property
    def done(self) -> bool:
        """
        Flag indicating whether the system is done for the day
        """
        return self._done

    @property
    def periods(self) -> List[pendulum.DateTime]:
        return self._periods

    def fetch(self, data: List[Dict]) -> None:
        """
        A placeholder for the fetch function with data argument
        """
        pass

    def square_off(self) -> None:
        """
        Function to be run to square off positions
        """
        pass

    def get_timespan(self) -> List[pendulum.DateTime]:
        """
        Get the default timespan
        """
        return self.SYSTEM_END_TIME - self.SYSTEM_START_TIME

    def get_time_periods(self) -> List[pendulum.DateTime]:
        """
        Get time periods in timespan as a list
        """
        timespan = self.get_timespan()
        periods = [x for x in timespan.range(unit="seconds", amount=self.INTERVAL)]
        return periods

    def get_next_scan(self) -> pendulum.DateTime:
        """
        Get the next scan
        """
        now = pendulum.now(tz=self.TZ)
        to_remove = []
        for p in self.periods:
            if p < now:
                to_remove.append(p)
            else:
                break
        for r in to_remove:
            self._periods.remove(r)
        return p

    def run(self, data: List[Dict] = []) -> None:
        now = pendulum.now(tz=self.TZ)
        if now > self.SYSTEM_START_TIME:
            self.fetch(data)
            self.entry()
            self.exit()
            self._cycle += 1
        # Square off positions
        if now > self.SQUARE_OFF_TIME:
            # Run code to square off
            self.square_off()

    @staticmethod
    def stop_loss_by_value(price: float, stop: float, side: str) -> float:
        """
        Get stop loss by value
        price
            price from which stop is to be calculated
        stop
            fixed stop value in points
        side
            BUY/SELL
        >>> base = BaseSystem()
        >>> base.stop_loss_by_value(100,3,'BUY')
        97.0
        >>> base.stop_loss_by_value(100,3,'SELL')
        103.0
        >>> base.stop_loss_by_value(100,1,'SOME')
        100.0
        """
        if side == "BUY":
            return float(price - stop)
        elif side == "SELL":
            return float(price + stop)
        else:
            return float(price)

    @staticmethod
    def stop_loss_by_percentage(price: float, stop: float, side: str) -> float:
        """
        Get stop loss by percentage
        Enter the actual percentage (not as decimals)
        price
            price from which stop is to be calculated
        stop
            stop value in percentage
        side
            BUY/SELL
        >>> base = BaseSystem()
        >>> base.stop_loss_by_percentage(100,2,'BUY')
        98.0
        >>> base.stop_loss_by_percentage(100,2,'SELL')
        102.0
        >>> base.stop_loss_by_percentage(100,2,'WHAT')
        100.0
        """
        percent = stop * 0.01
        if side == "BUY":
            return float(price * (1 - percent))
        elif side == "SELL":
            return float(price * (1 + percent))
        else:
            return float(price)

    def get_quantity(
        self, price: Optional[float] = None, stop: Optional[float] = None
    ) -> int:
        """
        Get quantity for the stock based on the
        pre-defined risk weightage method
        price
            should be provided if weightage is capital
        stop
            should be provided if weightage is risk
        >>> base = BaseSystem()
        >>> base.get_quantity()
        0
        >>> base.get_quantity(price=1000)
        100
        >>> base = BaseSystem(WEIGHTAGE='risk')
        >>> base.get_quantity(stop=50)
        20
        """
        # Return 0 if both price and stop not provided
        if not (price) and not (stop):
            return 0
        if self.WEIGHTAGE == "risk":
            if stop:
                return int(self.RISK_PER_STOCK / stop)
            else:
                return 0
        else:
            if price:
                return int(self.CAPITAL_PER_STOCK / price)
            else:
                return 0


class Candle(BaseModel):
    """
    A model representing a single candle
    """

    timestamp: pendulum.DateTime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[int]
    info: Optional[Any]


class CandleStick(BaseModel):
    """
    Class to work on candlesticks
    """

    name: str
    candles: List[Candle] = []
    initial_price: float = 0
    ltp: float = 0
    high: float = -1  # Initialize to a impossible value
    low: float = 1e10  # Initialize to a impossible value
    bar_high: float = -1  # Initialize to a impossible value
    bar_low: float = 1e10  # Initialize to a impossible value

    def add_candle(self, candle: Candle) -> None:
        """
        Add a candle
        """
        self.candles.append(deepcopy(candle))

    def update(self, ltp: float):
        """
        Update running candle
        """
        if self.initial_price == 0:
            self.initial_price = self.ltp
        self.ltp = ltp
        if self.initial_price == 0:
            self.initial_price = ltp
        self.bar_high = max(self.bar_high, ltp)
        self.bar_low = min(self.bar_low, ltp)
        self.high = max(self.high, ltp)
        self.low = min(self.low, ltp)

    def update_candle(self, timestamp: pendulum.DateTime = pendulum.now()) -> Candle:
        """
        Update and append the existing candle
        returns the updated candle
        """
        if len(self.candles) == 0:
            open_price = self.initial_price
        else:
            open_price = self.candles[-1].close
        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=self.bar_high,
            low=self.bar_low,
            close=self.ltp,
        )
        self.add_candle(candle)
        self.bar_high = self.bar_low = self.ltp
        return candle

    @property
    def bullish_bars(self) -> int:
        """
        Returns the number of bullish bars
        """
        count = 0
        for candle in self.candles:
            if candle.close > candle.open:
                count += 1
        return count

    @property
    def bearish_bars(self) -> int:
        """
        Returns the number of bullish bars
        """
        count = 0
        for candle in self.candles:
            if candle.close < candle.open:
                count += 1
        return count
