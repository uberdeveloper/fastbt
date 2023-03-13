import pytest
from fastbt.options.payoff import *


def test_option_contract_defaults():
    contract = OptionContract(strike=18000, option="c", side=1, premium=150, quantity=1)
    assert contract.strike == 18000
    assert contract.option == Opt.CALL
    assert contract.side == Side.BUY
    assert contract.premium == 150
    assert contract.quantity == 1


def test_payoff_defaults():
    p = OptionPayoff()
    assert p.spot == 0
    assert p._options == []
    assert p.options == []
