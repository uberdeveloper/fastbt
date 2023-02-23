from dataclasses import dataclass
from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from fastbt.Meta import Broker
import uuid
import pendulum
from collections import Counter, defaultdict


def get_option(spot: float, num: int = 0, step: float = 100.0) -> float:
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
    v = round(spot / step)
    return v * (step + num)


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
        self._spot: float = 0.00
        self._options: List[Dict] = []

    def _payoff(self, strike: float, option: str, position: str, **kwargs) -> float:
        """
        calculate the payoff for the option
        """
        comb = (option, position)
        spot = kwargs.get("spot", self.spot)
        if comb == ("C", "B"):
            return max(spot - strike, 0)
        elif comb == ("P", "B"):
            return max(strike - spot, 0)
        elif comb == ("C", "S"):
            return min(0, strike - spot)
        elif comb == ("P", "S"):
            return min(0, spot - strike)
        else:
            return 0

    def add(
        self,
        strike: float,
        opt_type: str = "C",
        position: str = "B",
        premium: float = 0.0,
        qty: int = 1,
    ) -> None:
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
        if position == "B":
            premium = 0 - abs(premium)
        elif position == "S":
            qty = 0 - abs(qty)
        self._options.append(
            {
                "strike": strike,
                "option": opt_type,
                "position": position,
                "premium": premium,
                "qty": qty,
            }
        )

    @property
    def options(self) -> List[Dict]:
        """
        return the list of options
        """
        return self._options

    def clear(self) -> None:
        """
        Clear all options
        """
        self._options = []

    @property
    def spot(self) -> float:
        return self._spot

    @spot.setter
    def spot(self, value):
        """
        Set the spot price
        """
        self._spot = value

    def calc(self, spot: Optional[float] = None) -> Union[List, None]:
        """
        Calculate the payoff
        """
        if not (spot):
            spot = self.spot
        payoffs = []
        for opt in self.options:
            profit = (self._payoff(**opt, spot=spot) + opt["premium"]) * abs(opt["qty"])
            payoffs.append(profit)
        return payoffs


def get_option_contracts(
    spot, name: str, step: float = 100, a: int = 0, b: int = 0, c: int = 0, d: int = 0
) -> List[Tuple[str, str, float]]:
    """
    Get the list of option contracts given strategy name
    See this reference on how the contracts are generated
    https://www.optionsplaybook.com/option-strategies/
    spot
        value of the underlying
    name
        name of the strategy
    step
        step size of the option
    a
        strike A steps away from atm
    b
        strike B steps away from atm
    c
        strike C steps away from atm
    d
        strike D steps away from atm
    Note
    -----
    1) atm is calculated as the nearest strike price to spot
    2) strikes a,b,c,d as in options playbook
    3) all the strikes may not be applicable to all the strategies
    """
    name = name.lower()
    contracts = []
    if name == "short_straddle":
        atm = get_option(spot, step=step)
        ctx1 = ("sell", "call", atm + a * step)
        ctx2 = ("sell", "put", atm - a * step)
        contracts.append(ctx1)
        contracts.append(ctx2)
        return contracts
    elif name == "short_strangle":
        atm = get_option(spot, step=step)
        if a == 0:
            a = 1
        if b == 0:
            b = 1
        ctx1 = ("sell", "put", atm - a * step)
        ctx2 = ("sell", "call", atm + b * step)
        contracts.append(ctx1)
        contracts.append(ctx2)
        return contracts
    elif name == "long_straddle":
        atm = get_option(spot, step=step)
        ctx1 = ("buy", "call", atm + a * step)
        ctx2 = ("buy", "put", atm - a * step)
        contracts.append(ctx1)
        contracts.append(ctx2)
        return contracts
    elif name == "long_strangle":
        atm = get_option(spot, step=step)
        if a == 0:
            a = 1
        if b == 0:
            b = 1
        ctx1 = ("buy", "put", atm - a * step)
        ctx2 = ("buy", "call", atm + b * step)
        contracts.append(ctx1)
        contracts.append(ctx2)
        return contracts
    return contracts


@dataclass
class Order:
    symbol: str
    side: str
    quantity: int = 1
    internal_id: Optional[str] = None
    parent_id: Optional[str] = None
    timestamp: Optional[pendulum.DateTime] = None
    order_type: str = "MARKET"
    broker_timestamp: Optional[pendulum.DateTime] = None
    exchange_timestamp: Optional[pendulum.DateTime] = None
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    price: Optional[float] = None
    trigger_price: float = 0.0
    average_price: float = 0.0
    pending_quantity: Optional[int] = None
    filled_quantity: int = 0
    cancelled_quantity: int = 0
    disclosed_quantity: int = 0
    validity: str = "DAY"
    status: Optional[str] = None
    expires_in: int = 0
    timezone: str = "UTC"
    client_id: Optional[str] = None
    convert_to_market_after_expiry: bool = False
    cancel_after_expiry: bool = True
    retries: int = 0
    exchange: Optional[str] = None
    tag: Optional[str] = None

    def __post_init__(self) -> None:
        self.internal_id = uuid.uuid4().hex
        tz = self.timezone
        self.timestamp = pendulum.now(tz=tz)
        self.pending_quantity = self.quantity
        self._attrs: List[str] = [
            "exchange_timestamp",
            "exchange_order_id",
            "status",
            "filled_quantity",
            "pending_quantity",
            "disclosed_quantity",
            "average_price",
        ]
        if self.expires_in == 0:
            self.expires_in = (
                pendulum.today(tz=tz).end_of("day") - pendulum.now(tz=tz)
            ).seconds
        else:
            self.expires_in = abs(self.expires_in)

    @property
    def is_complete(self) -> bool:
        if self.quantity == self.filled_quantity:
            return True
        elif self.status == "COMPLETE":
            return True
        elif (self.filled_quantity + self.cancelled_quantity) == self.quantity:
            return True
        else:
            return False

    @property
    def is_pending(self) -> bool:
        quantity = self.filled_quantity + self.cancelled_quantity
        if self.status == "COMPLETE":
            return False
        elif quantity < self.quantity:
            return True
        else:
            return False

    @property
    def time_to_expiry(self) -> int:
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        return max(0, self.expires_in - (now - ts).seconds)

    @property
    def time_after_expiry(self) -> int:
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        return max(0, (now - ts).seconds - self.expires_in)

    @property
    def has_expired(self) -> bool:
        return True if self.time_to_expiry == 0 else False

    @property
    def has_parent(self) -> bool:
        return True if self.parent_id else False

    def update(self, data: Dict[str, Any]) -> bool:
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
        if not (self.is_complete):
            for att in self._attrs:
                val = data.get(att)
                if val:
                    setattr(self, att, val)
            return True
        else:
            return False

    def execute(self, broker: Broker, **kwargs) -> Optional[str]:
        """
        Execute an order on a broker, place a new order
        kwargs
            Additional arguments to the order
        Note
        ----
        Only new arguments added to the order in keyword arguments
        """
        # Do not place a new order if this order is complete or has order_id
        if not (self.is_complete) and not (self.order_id):
            order_args = {
                "symbol": self.symbol.upper(),
                "side": self.side.upper(),
                "order_type": self.order_type.upper(),
                "quantity": self.quantity,
                "price": self.price,
                "trigger_price": self.trigger_price,
                "disclosed_quantity": self.disclosed_quantity,
            }
            dct = {k: v for k, v in kwargs.items() if k not in order_args.keys()}
            order_args.update(dct)
            order_id = broker.order_place(**order_args)
            self.order_id = order_id
            return order_id
        else:
            return self.order_id

    def modify(self, broker: Broker, **kwargs):
        """
        Modify an existing order
        """
        order_args = {
            "order_id": self.order_id,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "order_type": self.order_type.upper(),
            "disclosed_quantity": self.disclosed_quantity,
        }
        dct = {k: v for k, v in kwargs.items() if k not in order_args.keys()}
        order_args.update(dct)
        broker.order_modify(**order_args)

    def cancel(self, broker: Broker):
        """
        Cancel an existing order
        """
        broker.order_cancel(order_id=self.order_id)


@dataclass
class CompoundOrder:
    broker: Type[Broker]
    internal_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.internal_id = uuid.uuid4().hex
        self._ltp: defaultdict = defaultdict()
        self._orders: List[Order] = []

    @property
    def orders(self) -> List[Order]:
        return self._orders

    @property
    def count(self) -> int:
        """
        return the number of orders
        """
        return len(self.orders)

    @property
    def ltp(self) -> defaultdict:
        return self._ltp

    @property
    def positions(self) -> Counter:
        """
        return the positions as a dictionary
        """
        c: Counter = Counter()
        for order in self.orders:
            symbol = order.symbol
            qty = order.filled_quantity
            side = str(order.side).lower()
            sign = -1 if side == "sell" else 1
            qty = qty * sign
            c.update({symbol: qty})
        return c

    def add_order(self, **kwargs) -> Optional[str]:
        kwargs["parent_id"] = self.internal_id
        order = Order(**kwargs)
        self._orders.append(order)
        return order.internal_id

    def _average_price(self, side: str = "buy") -> Dict[str, float]:
        """
        Get the average price for all the instruments
        side
            side to calculate average price - buy or sel
        """
        side = str(side).lower()
        value_counter: Counter = Counter()
        quantity_counter: Counter = Counter()
        for order in self.orders:
            order_side = str(order.side).lower()
            if side == order_side:
                symbol = order.symbol
                price = order.average_price
                quantity = order.filled_quantity
                value = price * quantity
                value_counter.update({symbol: value})
                quantity_counter.update({symbol: quantity})
        dct: defaultdict = defaultdict()
        for v in value_counter:
            numerator = value_counter.get(v)
            denominator = quantity_counter.get(v)
            if numerator and denominator:
                dct[v] = numerator / denominator
        return dct

    @property
    def average_buy_price(self) -> Dict[str, float]:
        return self._average_price(side="buy")

    @property
    def average_sell_price(self) -> Dict[str, float]:
        return self._average_price(side="sell")

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        returns a dictionary with order_id and update status as boolean
        """
        dct: Dict[str, bool] = {}
        for order in self.orders:
            order_id = str(order.order_id)
            status = order.status
            if (order_id in data) and (status != "COMPLETE"):
                d = data.get(order_id)
                if d:
                    order.update(d)
                    dct[order_id] = True
                else:
                    dct[order_id] = False
            else:
                dct[order_id] = False
        return dct

    def _total_quantity(self) -> Dict[str, Counter]:
        """
        Get the total buy and sell quantity by symbol
        """
        buy_counter: Counter = Counter()
        sell_counter: Counter = Counter()
        for order in self.orders:
            side = order.side.lower()
            symbol = order.symbol
            quantity = abs(order.filled_quantity)
            if side == "buy":
                buy_counter.update({symbol: quantity})
            elif side == "sell":
                sell_counter.update({symbol: quantity})
        return {"buy": buy_counter, "sell": sell_counter}

    @property
    def buy_quantity(self) -> Counter:
        return self._total_quantity()["buy"]

    @property
    def sell_quantity(self) -> Counter:
        return self._total_quantity()["sell"]

    def update_ltp(self, last_price: Dict[str, float]):
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
    def net_value(self) -> Counter:
        """
        Return the net value by symbol
        """
        c: Counter = Counter()
        for order in self.orders:
            symbol = order.symbol
            side = str(order.side).lower()
            sign = -1 if side == "sell" else 1
            value = order.filled_quantity * order.average_price * sign
            c.update({symbol: value})
        return c

    @property
    def mtm(self) -> Counter:
        c: Counter = Counter()
        net_value = self.net_value
        positions = self.positions
        ltp = self.ltp
        for symbol, value in net_value.items():
            c.update({symbol: -value})
        for symbol, quantity in positions.items():
            v = quantity * ltp.get(symbol, 0)
            c.update({symbol: v})
        return c

    @property
    def total_mtm(self) -> float:
        return sum(self.mtm.values())

    def execute_all(self):
        for order in self.orders:
            order.execute(broker=self.broker)

    def check_flags(self):
        """
        Check for flags on each order and take suitable action
        """
        for order in self.orders:
            if (order.is_pending) and (order.has_expired):
                if order.convert_to_market_after_expiry:
                    order.order_type = "MARKET"
                    order.modify(self.broker)
                elif order.cancel_after_expiry:
                    order.cancel(broker=self.broker)

    @property
    def completed_orders(self) -> List[Order]:
        return [order for order in self.orders if order.is_complete]

    @property
    def pending_orders(self) -> List[Order]:
        return [order for order in self.orders if order.is_pending]


class StopOrder(CompoundOrder):
    def __init__(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        price: float = 0.0,
        quantity: int = 1,
        order_type="MARKET",
        disclosed_quantity: int = 0,
        order_args: Optional[Dict] = None,
        **kwargs,
    ):
        super(StopOrder, self).__init__(**kwargs)
        side2 = "sell" if side.lower() == "buy" else "buy"
        self.add_order(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            disclosed_quantity=disclosed_quantity,
        )
        self.add_order(
            symbol=symbol,
            side=side2,
            price=0,
            trigger_price=trigger_price,
            quantity=quantity,
            order_type="SL-M",
            disclosed_quantity=disclosed_quantity,
        )


class StopLimitOrder(CompoundOrder):
    def __init__(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        price: float = 0.0,
        stop_limit_price: float = 0.0,
        quantity: int = 1,
        order_type="MARKET",
        disclosed_quantity: int = 0,
        order_args: Optional[Dict] = None,
        **kwargs,
    ):
        super(StopLimitOrder, self).__init__(**kwargs)
        side2 = "sell" if side.lower() == "buy" else "buy"
        if stop_limit_price == 0:
            stop_limit_price = trigger_price
        self.add_order(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            disclosed_quantity=disclosed_quantity,
        )
        self.add_order(
            symbol=symbol,
            side=side2,
            price=stop_limit_price,
            trigger_price=trigger_price,
            quantity=quantity,
            order_type="SL",
            disclosed_quantity=disclosed_quantity,
        )


class BracketOrder(StopOrder):
    def __init__(self, target: float, **kwargs):
        super(BracketOrder, self).__init__(**kwargs)
        self._target = target

    @property
    def target(self) -> float:
        return self._target

    @property
    def is_target_hit(self) -> bool:
        """
        Check whether the given target is hit
        """
        for k, v in self.ltp.items():
            # We assume a single symbol only so breaking
            # TO DO: A better way is appreciated
            ltp = v
            break
        return True if ltp > self.target else False

    def do_target(self) -> None:
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
            order.order_type = "MARKET"
            order.modify(broker=self.broker)


class OptionStrategy:
    """
    Option Strategy is a list of compound orders
    """

    def __init__(self, broker: Type[Broker], profit=1e100, loss=-1e100) -> None:
        self._orders: List[CompoundOrder] = []
        self._broker: Type[Broker] = broker
        self._ltp: defaultdict = defaultdict()
        self.profit: float = profit
        self.loss: float = loss

    @property
    def broker(self) -> Type[Broker]:
        return self._broker

    @property
    def orders(self) -> List[CompoundOrder]:
        return self._orders

    def add_order(self, order: CompoundOrder) -> None:
        """
        Add a compound order
        broker is overriden
        """
        order.broker = self.broker
        self._orders.append(order)

    @property
    def all_orders(self) -> List[Order]:
        """
        Get the list of all orders
        """
        orders = []
        for order in self.orders:
            orders.extend(order.orders)
        return orders

    def update_ltp(self, last_price: Dict[str, float]) -> List[Any]:
        """
        Update ltp for the given symbols
        last_price
            dictionary with symbol as key and last price as value
        """
        return self._call("update_ltp", last_price=last_price)

    def _call(self, attribute: str, **kwargs) -> List[Any]:
        """
        Call the given method or property on each of the compound orders
        attribute
            property or method
        kwargs
            keyword arguments to be called in case of a method
        returns a list of the return values
        Note
        -----
        1) An attribtute is considered to be a method if callable returns True
        """
        responses = []
        for order in self.orders:
            attr = getattr(order, attribute, None)
            if callable(attr):
                responses.append(attr(**kwargs))
            else:
                responses.append(attr)
        return responses

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> List[Any]:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        returns a dictionary with order_id and update status as boolean
        for all compound orders
        """
        return self._call("update_orders", data=data)

    def execute_all(self) -> List[Any]:
        """
        Execute all orders in all compound orders
        """
        return self._call("execute_all")

    @property
    def total_mtm(self) -> float:
        """
        Returns the total mtm for this strategy
        """
        mtm = self._call("total_mtm")
        return sum([x for x in mtm if x is not None])

    @property
    def positions(self) -> Counter:
        """
        Return the combined positions for this strategy
        """
        c: Counter = Counter()
        positions = self._call("positions")
        for position in positions:
            c.update(position)
        return c

    @property
    def is_profit_hit(self) -> bool:
        return True if self.total_mtm > self.profit else False

    @property
    def is_loss_hit(self) -> bool:
        return True if self.total_mtm < self.loss else False

    @property
    def can_exit_strategy(self) -> bool:
        """
        Check whether we can exit from the strategy
        We can exit from the strategy if either of the following
        conditions is met
        1) Profit is hit
        2) Loss is hit
        """
        if self.is_profit_hit:
            return True
        elif self.is_loss_hit:
            return True
        else:
            return False


class OptionOrder(CompoundOrder):
    def __init__(
        self,
        symbol: str,
        spot: float,
        expiry: str,
        contracts: List[Tuple[int, str, str, int]],
        step: float = 100,
        fmt: Optional[Callable] = None,
        **kwargs,
    ):
        """
        Initialize your option order
        symbol
            base symbol to be used
        spot
            spot price of the underlying
        expiry
            expiry of the contract
        contracts
            list of contracts to be entered into, the contracts
            should be a list of 4-tuples with the elements being
            the (atm, buy or sell, put or call, qty)
            To buy the atm call and buy option, this should be
            [(0,c,b,1), (0,p,b,1)]
        step
            step size to calculate the strike prices
        fmt
            format to generate the option symbol as a function
            This function takes the symbol,expiry,strike,option_type and
            generates a option contract name
        """
        self.symbol = symbol
        self.spot = spot
        self.expiry = expiry
        self._contracts = contracts
        self.step = step
        if fmt:
            self._fmt_function = fmt
        else:

            def _format_function(symbol, expiry, strike, option_type):
                return f"{symbol}{expiry}{strike}{option_type}E".upper()

            self._fmt_function = _format_function
        super(OptionOrder, self).__init__(**kwargs)

    def _generate_strikes(self) -> List[Union[int, float]]:
        """
        Generate strikes for the contracts
        """
        strikes = []
        sign = {"C": 1, "P": -1}
        for c in self._contracts:
            strk = c[0]
            opt = c[1][0].upper()
            strike = (
                get_option(self.spot, step=self.step) + strk * sign[opt] * self.step
            )
            strikes.append(strike)
        return strikes

    def _generate_contract_names(self) -> List[str]:
        """
        Generate the list of contract names
        """
        strikes = self._generate_strikes()
        contract_names = []
        for c, s in zip(self._contracts, strikes):
            opt = c[1][0].upper()
            name = self._fmt_function(self.symbol, self.expiry, s, opt)
            contract_names.append(name)
        return contract_names

    def generate_orders(self, **kwargs) -> List[Order]:
        """
        Generate the list of orders to be placed
        kwargs
            other arguments to be added to the order
        """
        orders = []
        symbols = self._generate_contract_names()
        order_map = {"b": "buy", "s": "sell"}
        for symbol, contract in zip(symbols, self._contracts):
            side = order_map[contract[2][0].lower()]
            qty = contract[3]
            order = Order(symbol=symbol, side=side, quantity=qty, **kwargs)
            orders.append(order)
        return orders

    def add_all_orders(self, **kwargs):
        """
        Generate and add all the orders given in contracts
        """
        gen = self.generate_orders(**kwargs)
        for g in gen:
            self._orders.append(g)


@dataclass
class TrailingStopOrder(StopLimitOrder):
    """
    Trailing stop order
    """

    def __init__(self, trail_by: Tuple[float, float], **kwargs):
        self.trail_big: float = trail_by[0]
        self.trail_small: float = trail_by[-1]
        super(TrailingStopOrder, self).__init__(**kwargs)
        self._maxmtm: float = 0
        self._stop: float = kwargs.get("trigger_price", 0)
        self.initial_stop = self._stop
        self.symbol: str = kwargs.get("symbol")
        self.quantity: int = kwargs.get("quantity", 1)

    @property
    def stop(self):
        return self._stop

    @property
    def maxmtm(self):
        return self._maxmtm

    def _update_maxmtm(self):
        self._maxmtm = max(self.total_mtm, self._maxmtm)

    def _update_stop(self):
        mtm_per_unit = self.maxmtm / self.quantity
        multiplier = self.trail_small / self.trail_big
        self._stop = self.initial_stop + (mtm_per_unit * multiplier)

    def watch(self):
        self._update_maxmtm()
        self._update_stop()
        ltp = self.ltp.get(self.symbol)
        if ltp:
            # TODO: Implement for sell also
            if ltp < self.stop:
                order = self.orders[-1]
                order.order_type = "MARKET"
                order.modify(broker=self.broker)
