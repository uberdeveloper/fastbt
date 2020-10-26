import pendulum
from typing import List, Tuple, Optional, Dict, Sequence, Any
from fastbt.Meta import TradingSystem
from pydantic import BaseModel, ValidationError, validator
from collections import defaultdict

# Declare global variables
TZ = 'Asia/Kolkata'
    
def tuple_to_time(tup:Tuple[int,int,int]=(0,0,0)) -> pendulum.DateTime:
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
    hour,minute,second = tup
    return pendulum.today(tz='Asia/Kolkata').add(hours=hour,minutes=minute,seconds=second)


def tick(price:float, tick_size:float=0.05) -> float:
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
    return round(round(price/tick_size)*tick_size,2)

def smart_buffer(price:float, side:str) -> float:
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
    sign = -1 if side == 'BUY' else 1
    if price < 50:
        return price
    elif price < 100:
        return round(price + (sign*0.05),2)
    elif price < 200:
        return round(price + (sign*0.10), 2)
    else:
        return round(tick(price + (sign*price*0.05*0.01)), 2)


class BaseSystem(TradingSystem):
    """
    This is an abstract system.
    Do not initialize it directly
    """
    # Declare default parameters
    _params =  {
            'INTERVAL': 60, # in seconds
            'MAX_POSITIONS': 10,
            # All parameters that end with TIME 
            # take a 3-tuple with hour,minute,second as arguments
            'SYSTEM_START_TIME': (9,15,0),
            'SYSTEM_END_TIME': (15,15,0),
            'TRADE_START_TIME': (9,16,0),
            'SQUARE_OFF_TIME': (15,15,0),
            'TZ': 'Asia/Kolkata',
            }

    def __init__(self, name:str='base_strategy', env:str='paper',
            broker:Any=None, **kwargs):
        for k,v in self._params.items():
            if k in kwargs:
                value = kwargs.get(k)
            else: 
                value = v
            if k.endswith('TIME'):
                value = tuple_to_time(value)
            setattr(self,k,value)
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

    def fetch(self, data:List[Dict]) -> None:
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
        periods = [x for x in timespan.range(unit='seconds',amount=self.INTERVAL)]
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
                for r in to_remove:
                    self._periods.remove(r)
                return p

    def run(self, data:List[Dict]=[]) -> None:
        now = pendulum.now(tz=self.TZ)
        if (now > self.SYSTEM_START_TIME):
            self.fetch(data)
            self.entry()
            self.exit()
            self._cycle += 1
        # Square off positions
        if now > self.SQUARE_OFF_TIME:
            # Run code to square off
           self.square_off() 

