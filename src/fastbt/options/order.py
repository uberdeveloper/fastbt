from dataclasses import dataclass
from typing import Optional, Dict, List, Type, Any, Union
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

class OptionPayoff:
    """
    A simple class for calculating option payoffs
    given spot prices and options
    1) Add your options with the add method
    2) Provide a spot price
    3) Call calculate to get the payoff for this spot price
    Note
    -----
    This class only does a simple arithmetic for the option and
    doesn't include any calculations for volatility or duration.
    It's assumed that the option is exercised at expiry and it
    doesn't have any time value
    """
    def __init__(self):
        self._spot:float = 0.00
        self._options:List[Dict] = []

    def _payoff(self, strike:float, option:str, position:str, **kwargs)->float:
        """
        calculate the payoff for the option
        """
        comb = (option, position)
        spot = kwargs.get('spot', self.spot)
        if comb == ('C', 'B'):
            return max(spot-strike, 0)
        elif comb == ('P', 'B'):
            return max(strike-spot, 0)
        elif comb == ('C', 'S'):
            return min(0, strike-spot)
        elif comb == ('P', 'S'):
            return min(0, spot-strike)
        else:
            return 0

    def add(self, strike:float, opt_type:str='C', position:str='B', premium:float=0.0, qty:int=1)->None:
        """
        Add an option
        strike
            strike price of the options
        opt_type
            option type - C for call and P for put
        position
            whether you are Buying or Selling the option
            B for buy and S for sell
        premium
            option premium
        qty
            quantity of options contract
        """
        if position == 'B':
            premium = 0-abs(premium)
        elif position == 'S':
            qty = 0-abs(qty)
        self._options.append({
            'strike': strike,
            'option': opt_type,
            'position': position,
            'premium': premium,
            'qty': qty
            })

    @property
    def options(self)->List[Dict]:
        """
        return the list of options
        """
        return self._options

    def clear(self)->None:
        """
        Clear all options
        """
        self._options = []

    @property
    def spot(self)->float:
        return self._spot

    @spot.setter
    def spot(self, value):
        """
        Set the spot price
        """
        self._spot = value 

    def calc(self, spot:Optional[float]=None)->Union[List, None]:
        """
        Calculate the payoff
        """
        if not(spot):
            spot = self.spot
        payoffs = []
        for opt in self.options:
            profit = (self._payoff(**opt, spot=spot) + opt['premium']) * abs(opt['qty'])
            payoffs.append(profit)
        return payoffs


@dataclass
class Order:
    symbol:str
    side:str
    quantity:int=1
    internal_id:Optional[str] = None
    timestamp:Optional[pendulum.DateTime] = None
    order_type:str = 'MARKET' 
    broker_timestamp:Optional[pendulum.DateTime] = None
    exchange_timestamp:Optional[pendulum.DateTime] = None
    order_id:Optional[str] = None
    exchange_order_id:Optional[str] = None
    price:Optional[float] = None
    trigger_price:float = 0.0
    average_price:float = 0.0
    pending_quantity:Optional[int] = None
    filled_quantity:int = 0 
    cancelled_quantity:int = 0 
    disclosed_quantity:int = 0 
    validity:str = 'DAY'
    status:Optional [str] = None

    def __post_init__(self)->None:
        self.internal_id = uuid.uuid4().hex
        self.timestamp = pendulum.now()
        self.pending_quantity = self.quantity
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

    def update(self, data:Dict)->bool:
        """
        Update order based on information received from broker
        data
            data to update as dictionary
        returns True if update is done
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
            return True
        else:
            return False
    
    def execute(self, broker:Broker, **kwargs):
        """
        Execute an order on a broker, place a new order
        kwargs
            Additional arguments to the order
        Note
        ----
        Only new arguments added to the order in keyword arguments
        """
        # Do not place a new order if this order is complete or has order_id
        if not(self.is_complete) and not(self.order_id):
            order_args = {
                'symbol': self.symbol.upper(),
                'side': self.side.upper(),
                'order_type': self.order_type.upper(),
                'quantity': self.quantity,
                'price': self.price,
                'trigger_price': self.trigger_price,
                'disclosed_quantity': self.disclosed_quantity
            }
            dct = {k:v for k,v in kwargs.items() if k not in order_args.keys()}
            order_args.update(dct)
            order_id = broker.order_place(**order_args)
            self.order_id = order_id
            return order_id
        else:
            return self.order_id

    def modify(self, broker:Broker, **kwargs):
        """
        Modify an existing order
        """
        order_args = {
            'order_id': self.order_id,
            'quantity': self.quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'order_type': self.order_type.upper(),
            'disclosed_quantity': self.disclosed_quantity
        }
        dct = {k:v for k,v in kwargs.items() if k not in order_args.keys()}
        order_args.update(dct)
        broker.order_modify(**order_args)

    def cancel(self, broker:Broker):
        """
        Cancel an existing order
        """
        broker.order_cancel(order_id=self.order_id)

class CompoundOrder:
    def __init__(self, broker:Type[Broker]):
        self._orders:List[Order] = []
        self._broker:Type[Broker] = broker
        self._ltp:defaultdict = defaultdict()

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
    def ltp(self):
        return self._ltp

    @property
    def positions(self)->Counter:
        """
        return the positions as a dictionary
        """
        c:Counter = Counter()
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

    def _average_price(self, side:str='buy')->Dict[str,float]:
        """
        Get the average price for all the instruments
        side
            side to calculate average price - buy or sel    
        """
        side = str(side).lower()
        value_counter:Counter = Counter()
        quantity_counter:Counter = Counter()
        for order in self.orders:
            order_side = str(order.side).lower()
            if side == order_side:
                symbol = order.symbol
                price = order.average_price
                quantity = order.filled_quantity
                value = price*quantity
                value_counter.update({symbol: value})
                quantity_counter.update({symbol: quantity})
        dct:defaultdict = defaultdict()
        for v in value_counter:
            dct[v] = value_counter.get(v)/quantity_counter.get(v)
        return dct 

    @property
    def average_buy_price(self)->Dict[str,float]:
        return self._average_price(side='buy')

    @property
    def average_sell_price(self)->Dict[str,float]:
        return self._average_price(side='sell')

    def update_orders(self, data:Dict[str,Dict[str,Any]])->Dict[str,bool]:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        returns a dictionary with order_id and update status as boolean
        """
        dct = {}
        for order in self.orders:
            order_id = order.order_id
            status = order.status
            if (order_id in data) and (status!='COMPLETE'):
                d = data.get(order_id)
                order.update(d)
                dct[order_id] = True
            else:
                dct[order_id] = False
        return dct

    def _total_quantity(self)->Dict[str,Counter]:
        """
        Get the total buy and sell quantity by symbol
        """
        buy_counter:Counter = Counter()
        sell_counter:Counter = Counter()
        for order in self.orders:
            side = order.side.lower()
            symbol = order.symbol
            quantity = abs(order.filled_quantity)
            if side == 'buy':
                buy_counter.update({symbol: quantity})
            elif side == 'sell':
                sell_counter.update({symbol: quantity})
        return {'buy': buy_counter, 'sell': sell_counter}

    @property
    def buy_quantity(self):
        return self._total_quantity()['buy']

    @property
    def sell_quantity(self):
        return self._total_quantity()['sell']

    def update_ltp(self, last_price:Dict[str,float]):
        """
        Update ltp for the given symbols
        last_price
            dictionary with symbol as key and last price as value
        returns the ltp for all the symbols
        Note
        ----
        1. Last price is updated for all given symbols irrespective of 
        orders placed
        """
        for symbol, ltp in last_price.items():
            self._ltp[symbol] = ltp
        return self.ltp

    @property
    def net_value(self)->Counter:
        """
        Return the net value by symbol
        """    
        c:Counter = Counter()
        for order in self.orders:
            symbol = order.symbol
            side = str(order.side).lower()
            sign = -1 if side == 'sell' else 1
            value = order.filled_quantity * order.average_price * sign
            c.update({symbol:value})
        return c  

    @property
    def mtm(self)->Counter:
        c:Counter = Counter()
        net_value = self.net_value
        positions = self.positions
        ltp = self.ltp
        for symbol,value in net_value.items():
            c.update({symbol:-value})
        for symbol,quantity in positions.items():
            v = quantity * ltp.get(symbol, 0)
            c.update({symbol:v})
        return c

    @property
    def total_mtm(self)->float:
        return sum(self.mtm.values())

class StopOrder(CompoundOrder):
    def __init__(self, symbol:str, side:str, trigger_price:float,
        price:float=0.0, quantity:int=1, order_type='MARKET',
        disclosed_quantity:int=0, order_args:Optional[Dict]=None, **kwargs):        
        super(StopOrder, self).__init__(**kwargs)
        side2 = 'sell' if side.lower() == 'buy' else 'buy'
        self.add_order(symbol=symbol, side=side, price=price,
        quantity=quantity, order_type=order_type,
        disclosed_quantity=disclosed_quantity)
        self.add_order(symbol=symbol, side=side2, price=0,
        trigger_price=trigger_price, quantity=quantity, order_type='SL-M',
        disclosed_quantity=disclosed_quantity)

    def execute_all(self):
        for order in self.orders:
            order.execute(broker=self.broker)

class BracketOrder(StopOrder):
    def __init__(self, target:float, **kwargs):
        super(BracketOrder, self).__init__(**kwargs)
        self._target = target

    @property
    def target(self):
        return self._target

    @property
    def is_target_hit(self)->bool:
        """
        Check whether the given target is hit
        """
        for k,v in self.ltp.items():
            # We assume a single symbol only so breaking
            # TO DO: A better way is appreciated
            ltp = v
            break
        return True if ltp > self.target else False

    def do_target(self)->None:
        """
        Execute target order if target is hit
        Note
        -----
        This checks
         1. whether the target is hit
         2. if target is hit, modify the existing stop and exit the order
        """
        if self.is_target_hit:
            order = self.orders[-1]
            order.order_type = 'MARKET'
            order.modify(broker=self.broker)

class OptionStrategy:
    """
    Option Strategy is a list of compound orders
    """
    def __init__(self, broker:Type[Broker])->None:
        self._orders:List[CompoundOrder] = []
        self._broker:Type[Broker] = broker
        self._ltp:defaultdict = defaultdict()

    @property
    def broker(self):
        return self._broker

    @property
    def orders(self):
        return self._orders

    def add_order(self, order:CompoundOrder)->None:
        """
        Add a compound order
        broker is overriden
        """
        order._broker = self.broker
        self._orders.append(order)

    @property
    def all_orders(self)->List[Order]:
        """
        Get the list of all orders
        """
        orders = []
        for order in self.orders:
            orders.extend(order.orders)
        return orders

    def update_ltp(self, last_price:Dict[str,float]):
        """
        Update ltp for the given symbols
        last_price
            dictionary with symbol as key and last price as value
        """
        for order in self.orders:
            order.update_ltp(last_price)