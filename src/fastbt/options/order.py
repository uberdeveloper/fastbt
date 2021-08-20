from dataclasses import dataclass
from typing import Optional, Dict, List, Type
from fastbt.Meta import Broker
import uuid
import pendulum
from collections import Counter, defaultdict

def get_option(spot:float,num:int=0,step:float=100.0)->float:
    """
    Get the option price given number of strikes
    spot
	    spot price of the instrument
    num
        number of strikes farther
    step
        step size of the option
    Note
    ----
    1. By default, the ATM option is fetched
    """
    v = round(spot/step)
    return v*(step+num)

@dataclass
class Order:
    symbol:str
    side:str
    quantity:int=1
    internal_id:Optional[str] = None
    timestamp:Optional[pendulum.datetime] = None
    order_type:str = 'MARKET' 
    broker_timestamp:Optional[pendulum.datetime] = None
    exchange_timestamp:Optional[pendulum.datetime] = None
    order_id:Optional[str] = None
    exchange_order_id:Optional[str] = None
    price:Optional[float] = None
    trigger_price:float = 0.0
    average_price:Optional[float] = None
    pending_quantity:Optional[int] = None
    filled_quantity:int = 0 
    cancelled_quantity:int = 0 
    disclosed_quantity:int = 0 
    validity:str = 'DAY'
    status:Optional [str] = None

    def __post_init__(self)->None:
        self.internal_id = uuid.uuid4().hex
        self.timestamp = pendulum.now()
        self._attrs:List[str] = [
            'exchange_timestamp',
            'exchange_order_id',
            'status',
            'filled_quantity',
            'pending_quantity',
            'disclosed_quantity',
            'average_price'
            ]

    @property
    def is_complete(self)->bool:
        if self.quantity == self.filled_quantity:
            return True
        elif self.status == 'COMPLETE':
            return True
        elif (self.filled_quantity+self.cancelled_quantity) == self.quantity:
            return True
        else:
            return False

    @property
    def is_pending(self)->bool:
        quantity = self.filled_quantity + self.cancelled_quantity
        if self.status == 'COMPLETE':
            return False
        elif quantity < self.quantity:
            return True
        else:
            return False

    def update(self, data:Dict)->None:
        """
        Update order based on information received from broker
        data
            data to update as dictionary
        Note
        ----
        1) Information is updated only for those keys specified in attrs
        2) Information is updated only when the order is not completed
        """
        if not(self.is_complete):
            for att in self._attrs:
                val = data.get(att)
                if val:
                    setattr(self,att,val)



class CompoundOrder:
    def __init__(self, broker:Type[Broker]):
        self._orders:List[Order] = []
        self._broker = broker

    @property
    def orders(self):
        return self._orders

    @property
    def broker(self):
        return self._broker

    @property
    def count(self):
        """
        return the number of orders
        """
        return len(self.orders)

    @property
    def positions(self)->Counter:
        """
        return the positions as a dictionary
        """
        c = Counter()
        for order in self.orders:
            symbol = order.symbol
            qty = order.filled_quantity
            side = str(order.side).lower()
            sign = -1 if side == 'sell' else 1
            qty = qty*sign
            c.update({symbol:qty})
        return c

    def add_order(self,**kwargs)->str:
        order = Order(**kwargs)
        self._orders.append(order)
        return order.internal_id

    @property
    def average_buy_price(self)->Dict[str,float]:
        value_counter = Counter()
        quantity_counter = Counter()
        for order in self.orders:
            side = str(order.side).lower()
            if side == 'buy':
                symbol = order.symbol
                price = order.average_price
                quantity = order.filled_quantity
                value = price*quantity
                value_counter.update({symbol: value})
                quantity_counter.update({symbol: quantity})
        
        dct = defaultdict()
        for v in value_counter:
            dct[v] = value_counter.get(v)/quantity_counter.get(v)
        return dct 

