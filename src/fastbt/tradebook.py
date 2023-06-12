from collections import Counter, defaultdict
from typing import Dict, List


class TradeBook:
    """
    TO DO:
    Add open, long, short positions
    """

    def __init__(self, name="tradebook"):
        self._name = name
        self._trades = defaultdict(list)
        self._values = Counter()
        self._positions = Counter()

    def __repr__(self):
        string = "{name} with {count} entries and {pos} positions"
        pos = sum([1 for x in self._positions.values() if x != 0])
        string = string.format(name=self._name, count=len(self.all_trades), pos=pos)
        return string

    @property
    def name(self) -> str:
        return self._name

    @property
    def trades(self) -> Dict[str, List[Dict]]:
        return self._trades

    @property
    def all_trades(self) -> List[Dict]:
        """
        return all trades as a single list
        """
        lst = []
        if self._trades:
            for k, v in self._trades.items():
                lst.extend(v)
        return lst

    @property
    def positions(self) -> Dict[str, int]:
        """
        return the positions of all symbols
        """
        return self._positions

    @property
    def values(self) -> Dict[str, float]:
        """
        return the values of all symbols
        """
        return self._values

    @property
    def o(self) -> int:
        """
        return the count of open positions in the tradebook
        """
        return sum([1 for pos in self.positions.values() if pos != 0])

    @property
    def l(self) -> int:
        """
        return the count of long positions in the tradebook
        """
        return sum([1 for pos in self.positions.values() if pos > 0])

    @property
    def s(self) -> int:
        """
        return the count of short positions in the tradebook
        """
        return sum([1 for pos in self.positions.values() if pos < 0])

    def add_trade(
        self,
        timestamp: str,
        symbol: str,
        price: float,
        qty: float,
        order: str,
        **kwargs,
    ) -> None:
        """
        Add a trade to the tradebook
        timestamp
                python/pandas timestamp
        symbol
                an unique identifier for the security
        price
                price of the security
        qty
                quantity of the security
        order
                B/BUY for B and S/SELL for SELL
        kwargs
                any other arguments as a dictionary
        """
        o = {"B": 1, "S": -1}
        order = order.upper()[0]
        q = qty * o[order]
        dct = {
            "ts": timestamp,
            "symbol": symbol,
            "price": price,
            "qty": q,
            "order": order,
        }
        dct.update(kwargs)
        self._trades[symbol].append(dct)
        self._positions.update({symbol: q})
        value = q * price * -1
        self._values.update({symbol: value})

    def clear(self) -> None:
        """
        clear all existing entries
        """
        self._trades = defaultdict(list)
        self._values = Counter()
        self._positions = Counter()
        self._trades = defaultdict(list)

    def remove_trade(self, symbol: str):
        """
        Remove the last trade for the given symbol
        and adjust the positions and values
        """
        trades = self._trades.get(symbol)
        if trades:
            if len(trades) > 0:
                trade = trades.pop()
                q = trade["qty"] * -1
                value = q * trade["price"] * -1
                self._positions.update({symbol: q})
                self._values.update({symbol: value})

    def mtm(self, prices: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate the mtm for the given positions given
        the current prices
        price
            current prices of the symbols
        """
        values: Dict = Counter()
        for k, v in self.positions.items():
            if abs(v) > 0:
                ltp = prices.get(k)
                if ltp is None:
                    raise ValueError(f"{k} not given in prices")
                else:
                    values[k] = v * ltp
        values.update(self.values)
        return values

    @property
    def open_positions(self) -> Dict[str, float]:
        """
        return the list of open positions
        """
        return {k: v for k, v in self.positions.items() if abs(v) > 0}

    @property
    def long_positions(self) -> Dict[str, float]:
        """
        return the list of open positions
        """
        return {k: v for k, v in self.positions.items() if v > 0}

    @property
    def short_positions(self) -> Dict[str, float]:
        """
        return the list of open positions
        """
        return {k: v for k, v in self.positions.items() if v < 0}
