import unittest
import context
import pytest

from fastbt.tradebook import TradeBook

def test_name():
    tb = TradeBook()
    assert tb.name == 'tradebook'
    tb = TradeBook('myTradeBook')
    assert tb.name == 'myTradeBook'

def test_trades():
    tb = TradeBook()
    for i in range(100):
        tb.add_trade('2018-01-01', 'AAA', 100, 100, 'B')
    assert len(tb.trades) == 100
    tb.add_trade('2018-01-01', 'AAA', 100, 1, 'S')
    assert len(tb.trades) == 101
    counter = 101
    import random
    for i in range(5):
        r = random.randint(0,50)
        counter +=r
        for j in range(r):
            tb.add_trade('2018-01-01', 'MX', 100, r, 'S')
        assert len(tb.trades) == counter

def test_positions():
    tb = TradeBook()
    for i in range(10):
        tb.add_trade('2018-01-01', 'SNP', 18000, 1, 'B')
    assert len(tb.positions) == 1
    assert tb.positions['SNP'] == 10
    for i in range(5):
        tb.add_trade('2018-01-02', 'SNP', 19000, 1, 'S')
    assert tb.positions['SNP'] == 5
    tb.add_trade('2018-01-05', 'QQQ', 4300, 3, 'S')
    assert len(tb.positions) == 2
    assert tb.positions['QQQ'] == -3



