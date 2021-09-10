import unittest
import context
import pytest

from fastbt.tradebook import TradeBook
from collections import Counter


def test_name():
    tb = TradeBook()
    assert tb.name == "tradebook"
    tb = TradeBook("myTradeBook")
    assert tb.name == "myTradeBook"


def test_repr():
    tb = TradeBook("MyTradeBook")
    for i in range(10):
        tb.add_trade("2018-01-01", "AAA", 100, 100, "B")
    assert tb.__repr__() == "MyTradeBook with 10 entries and 1 positions"
    tb.add_trade("2018-01-01", "AAA", 110, 1000, "S")
    assert tb.__repr__() == "MyTradeBook with 11 entries and 0 positions"


def test_trades():
    tb = TradeBook()
    for i in range(100):
        tb.add_trade("2018-01-01", "AAA", 100, 100, "B")
    assert len(tb.all_trades) == 100
    tb.add_trade("2018-01-01", "AAA", 100, 1, "S")
    assert len(tb.all_trades) == 101
    counter = 101
    import random

    for i in range(5):
        r = random.randint(0, 50)
        counter += r
        for j in range(r):
            tb.add_trade("2018-01-01", "MX", 100, r, "S")
        assert len(tb.all_trades) == counter


def test_trades_multiple_symbols():
    tb = TradeBook()
    symbols = list("ABCD")
    trades = [10, 20, 30, 40]
    for i, j in zip(symbols, trades):
        for p in range(j):
            if p % 5 == 0:
                tb.add_trade("2019-01-01", i, 100, 10, "B", tag="mod")
            else:
                tb.add_trade("2019-01-01", i, 100, 10, "B")
    assert len(tb.trades["A"]) == 10
    assert len(tb.trades["B"]) == 20
    assert len(tb.trades["C"]) == 30
    assert len(tb.trades["D"]) == 40
    assert len(tb.all_trades) == 100
    assert sum([1 for d in tb.all_trades if d.get("tag")]) == 20


def test_trades_keyword_arguments():
    tb = TradeBook()
    dct = {
        "timestamp": "2019-01-01",
        "symbol": "AAAA",
        "price": 100,
        "qty": 10,
        "order": "B",
    }
    tb.add_trade(**dct)
    tb.add_trade(**dct, id=7)
    tb.add_trade(**dct, tag="x")
    tb.add_trade(**dct, tag="y")
    assert tb.trades["AAAA"][0]["price"] == 100
    assert tb.trades["AAAA"][1]["id"] == 7
    assert sum([1 for d in tb.all_trades if d.get("tag")]) == 2


def test_positions():
    tb = TradeBook()
    for i in range(10):
        tb.add_trade("2018-01-01", "SNP", 18000, 1, "B")
    assert len(tb.positions) == 1
    assert tb.positions["SNP"] == 10
    for i in range(5):
        tb.add_trade("2018-01-02", "SNP", 19000, 1, "S")
    assert tb.positions["SNP"] == 5
    tb.add_trade("2018-01-05", "QQQ", 4300, 3, "S")
    assert len(tb.positions) == 2
    assert tb.positions["QQQ"] == -3


class TestPositions(unittest.TestCase):
    def setUp(self):
        tb = TradeBook()
        tb.add_trade(1, "ABC", 75, 100, "B")
        tb.add_trade(1, "AAA", 76, 100, "B")
        tb.add_trade(1, "XYZ", 77, 100, "S")
        tb.add_trade(1, "XXX", 78, 100, "S")
        self.tb = tb

    def test_open_positions(self):
        assert self.tb.o == 4
        self.tb.add_trade(2, "ABC", 75, 100, "S")
        assert self.tb.o == 3

    def test_long_positions(self):
        assert self.tb.l == 2
        self.tb.add_trade(2, "MAB", 10, 10, "B")
        assert self.tb.l == 3
        self.tb.add_trade(2, "MAB", 10, 10, "S")
        self.tb.add_trade(1, "ABC", 75, 100, "S")
        self.tb.add_trade(1, "AAA", 76, 100, "S")
        assert self.tb.l == 0
        self.tb.add_trade(1, "AAA", 76, 100, "S")
        assert self.tb.l == 0

    def test_short_positions(self):
        assert self.tb.s == 2
        self.tb.add_trade(2, "XYZ", 77, 100, "B")
        self.tb.add_trade(2, "XXX", 78, 100, "B")
        assert self.tb.s == 0
        for i in range(10):
            self.tb.add_trade(i + 3, "MMM", 85, 10, "S")
        assert self.tb.s == 1

    def test_long_positions_two(self):
        assert self.tb.l == 2
        for i in range(10):
            self.tb.add_trade(i + 2, "AAA", 82, 10, "B")
        assert self.tb.l == 2
        for i in range(10):
            self.tb.add_trade(i + 12, "AAA" + str(i), 75, 10, "B")
            assert self.tb.l == i + 3


class TestValues(unittest.TestCase):
    def setUp(self):
        tb = TradeBook()
        tb.add_trade(1, "ABC", 75, 100, "B")
        tb.add_trade(1, "AAA", 76, 100, "B")
        tb.add_trade(1, "XYZ", 77, 100, "S")
        tb.add_trade(1, "XXX", 78, 100, "S")
        self.tb = tb

    def test_values(self):
        c = Counter(ABC=-7500, AAA=-7600, XYZ=7700, XXX=7800)
        assert self.tb.values == c

    def test_values_pnl(self):
        self.tb.add_trade(2, "ABC", 80, 100, "S")
        c = Counter(ABC=500, AAA=-7600, XYZ=7700, XXX=7800)
        assert self.tb.values == c

    def test_values_pnl_two(self):
        self.tb.add_trade(3, "XXX", 80, 100, "B")
        assert self.tb.values["XXX"] == -200
