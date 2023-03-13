import pytest
from fastbt.options.payoff import *


@pytest.fixture
def simple():
    return OptionPayoff()


def test_option_contract_defaults():
    contract = OptionContract(strike=18000, option="c", side=1, premium=150, quantity=1)
    assert contract.strike == 18000
    assert contract.option == Opt.CALL
    assert contract.side == Side.BUY
    assert contract.premium == 150
    assert contract.quantity == 1


def test_payoff_defaults(simple):
    p = simple
    assert p.spot == 0
    assert p._options == []
    assert p.options == []


def test_payoff_add_contract(simple):
    p = simple
    p.add_contract(14000, "c", -1, 120, 50)
    p.add_contract(14200, Opt.PUT, Side.BUY, 150, 50)
    assert len(p.options) == 2
    assert p.options[0].side == Side.SELL
    assert p.options[0].option == Opt.CALL


def test_add_payoff_add(simple):
    p = simple
    kwargs = dict(strike=12000, option="p", side=1, premium=100, quantity=50)
    kwargs2 = dict(strike=12400, option="c", side=-1, premium=100, quantity=50)
    p.add(OptionContract(**kwargs))
    p.add(OptionContract(**kwargs2))
    assert len(p.options) == 2
    assert p.options[0].side.value == 1
    assert p.options[0].option == "p"
