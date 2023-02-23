import random
from collections import defaultdict
from typing import Optional, List, Dict
from fastbt.models.base import BaseSystem
from fastbt.utils import tick
from pydantic import BaseModel
from copy import deepcopy


class StockData(BaseModel):
    name: str
    token: Optional[int]
    can_trade: bool = True
    positions: int = 0
    ltp: float = 0
    day_high: float = -1  # Impossible value for initialization
    day_low: float = 1e10  # Almost impossible value for initialization
    order_id: Optional[str]
    stop_id: Optional[str]
    stop_loss: Optional[float]
    high: Optional[float]
    low: Optional[float]


class HighLow(BaseModel):
    symbol: str
    high: float
    low: float


class Breakout(BaseSystem):
    """
    A simple breakout system
    Trades are taken when the given high or low is broke
    """

    def __init__(
        self, symbols: List[str], instrument_map: Dict[str, int] = {}, **kwargs
    ) -> None:
        """
        Initialize the strategy
        symbols
            list of symbols
        instrument_map
            dictionary mapping symbols to scrip code
        kwargs
            list of keyword arguments that could be passed to the
            strategy in addition to those inherited from base system
        """
        super(Breakout, self).__init__(**kwargs)
        self._data = defaultdict(StockData)
        self._instrument_map = instrument_map
        self._rev_map = {v: k for k, v in instrument_map.items() if v is not None}
        for symbol in symbols:
            self._data[symbol] = StockData(
                name=symbol, token=instrument_map.get(symbol)
            )

    def update_high_low(self, high_low: List[HighLow]) -> None:
        """
        Update the high and low values for breakout
        These values are used for calculating breakouts
        """
        for hl in high_low:
            if type(hl) == dict:
                hl = HighLow(**hl)
            print(hl, hl.symbol)
            d = self._data.get(hl.symbol)
            if d:
                d.high = hl.high
                d.low = hl.low

    def stop_loss(
        self, symbol: str, side: str, method: str = "auto", stop: float = 0
    ) -> float:
        """
        Get the stop loss for the symbol
        symbol
            name of the symbol
        side
            BUY/SELL
        method
            stop loss calculation method
        Note
        ----
        1) returns 0 if the method if the symbol is not found
        2) sl method reverts to auto in case of unknown string
        """

        def sl():
            # Internal function to calculate stop
            if side == "BUY":
                return float(self.data[symbol].low)
            elif side == "SELL":
                return float(self.data[symbol].high)
            else:
                return 0.0

        # TO DO: A better way to implement stop functions
        d = self.data.get(symbol)
        if d:
            ltp = d.ltp
            if method == "value":
                return self.stop_loss_by_value(price=ltp, side=side, stop=stop)
            elif method == "percent":
                return self.stop_loss_by_percentage(price=ltp, side=side, stop=stop)
            else:
                return sl()
        else:
            return 0.0

    def fetch(self, data: List[Dict]) -> None:
        """
        Update data
        """
        # Using get since we may me missing tokens
        for d in data:
            token = d.get("instrument_token")
            ltp = d.get("last_price")
            if token and ltp:
                symbol = self._rev_map.get(token)
                if symbol:
                    self._data[symbol].ltp = ltp

    def order(self, symbol: str, side: str, **kwargs):
        order_id = stop_id = None
        v = self.data[symbol]
        price = tick(v.ltp)
        stop = tick(self.stop_loss(symbol=symbol, side=side, stop=3, method="percent"))
        quantity = self.get_quantity(price=price, stop=stop)
        v.can_trade = False
        if side == "SELL":
            v.positions = 0 - quantity
        else:
            v.positions = quantity
        side_map = {"BUY": "SELL", "SELL": "BUY"}
        # Defaults for live order
        defaults = deepcopy(self.ORDER_DEFAULT_KWARGS)
        defaults.update(
            dict(
                symbol=symbol,
                order_type="LIMIT",
                price=price,
                quantity=quantity,
                side=side,
            )
        )
        defaults.update(kwargs)
        if self.env == "live":
            order_id = self.broker.order_place(**defaults)
            side2 = side_map.get(side)
            stop_args = dict(order_type="SL-M", trigger_price=stop, side=side2)
            defaults.update(stop_args)
            stop_id = self.broker.order_place(**defaults)
        else:
            order_id = random.randint(100000, 999999)
            stop_id = random.randint(100000, 999999)
        v.order_id = order_id
        v.stop_id = stop_id
        return (order_id, stop_id)

    def entry(self):
        """
        Positions entry
        An order is entered if the ltp is greater than high or low
        subject to the constraints and conditions
        Override this method for your own entry logic
        """
        if self.open_positions >= self.MAX_POSITIONS:
            return
        for k, v in self.data.items():
            # The instrument can be traded and should have no
            # open positions and ltp should be updated
            if (v.can_trade) and (v.ltp > 0):
                if v.positions == 0:
                    if v.ltp > v.high:
                        # Place a BUY order
                        print("BUY", k, v.ltp, v.high, v.low)
                        self.order(symbol=k, side="BUY")
                    elif v.ltp < v.low:
                        # Place a SELL order
                        self.order(symbol=k, side="SELL")
                        print("SELL", k, v.ltp, v.high, v.low)

    @property
    def open_positions(self):
        count = 0
        for k, v in self.data.items():
            if (v.positions != 0) or not (v.can_trade):
                count += 1
        return count
