import pytest
from fastbt.options.payoff import *


@pytest.fixture
def simple():
    return OptionPayoff()


@pytest.fixture
def contracts_list():
    contracts = [
        dict(strike=16000, option="c", side=1, premium=100, quantity=1),
        dict(strike=16000, option="p", side=1, premium=100, quantity=1),
        dict(strike=15900, option="p", side=-1, premium=85, quantity=1),
        dict(strike=15985, option="h", side=1, premium=0, quantity=1),
        dict(strike=16030, option="f", side=-1, premium=0, quantity=1),
    ]
    return [OptionContract(**kwargs) for kwargs in contracts]


def test_option_contract_defaults():
    contract = OptionContract(strike=18000, option="c", side=1, premium=150, quantity=1)
    assert contract.strike == 18000
    assert contract.option == Opt.CALL
    assert contract.side == Side.BUY
    assert contract.premium == 150
    assert contract.quantity == 1


def test_option_contract_option_types():
    contract = OptionContract(option="h", side=1, strike=15000)
    assert contract.premium == 0
    assert contract.option == Opt.HOLDING
    assert contract.strike == 15000
    assert contract.side == Side.BUY
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


def test_payoff_add(simple):
    p = simple
    kwargs = dict(strike=12000, option="p", side=1, premium=100, quantity=50)
    kwargs2 = dict(strike=12400, option="c", side=-1, premium=100, quantity=50)
    kwargs3 = dict(option="f", side=-1, strike=12500, quantity=50)
    p.add(OptionContract(**kwargs))
    p.add(OptionContract(**kwargs2))
    p.add(OptionContract(**kwargs3))
    assert len(p.options) == 3
    assert p.options[0].side.value == 1
    assert p.options[0].option == "p"
    assert p.options[2].option == Opt.FUTURE


def test_payoff_clear(simple):
    p = simple
    kwargs = dict(strike=12000, option="p", side=1, premium=100, quantity=50)
    kwargs2 = dict(strike=12400, option="c", side=-1, premium=100, quantity=50)
    kwargs3 = dict(option="f", side=-1, strike=12500, quantity=50)
    p.add(OptionContract(**kwargs))
    p.add(OptionContract(**kwargs2))
    p.add(OptionContract(**kwargs3))
    assert len(p.options) == 3
    p.clear()
    assert len(p.options) == 0


@pytest.mark.parametrize(
    "strike,option,spot,expected",
    [
        (18200, "c", 18178, 0),
        (18200, "p", 18178, 22),
        (18200, "f", 18395, 195),
        (18200, "f", 18100, -100),
        (18200, "h", 18100, -100),
    ],
)
def test_option_contract_value(strike, option, spot, expected):
    contract = OptionContract(
        strike=strike, option=option, side=Side.BUY, premium=150, quantity=1
    )
    assert contract.value(spot=spot) == expected


@pytest.mark.parametrize(
    "strike,option,side,premium,quantity,spot,expected",
    [
        (18200, "c", Side.BUY, 120, 1, 18175, -120),
        (18200, "c", Side.SELL, 120, 1, 18175, 120),
        (18234, "f", -1, 120, 1, 18245, -11),
        (18234, "h", 1, 0, 1, 18245, 11),
        (18200, "c", 1, 120, 1, 18290, -30),
        (18200, "p", 1, 100, 1, 18290, -100),
        (18200, "p", Side.SELL, 100, 1, 18200, 100),
        (18200, "p", Side.BUY, 100, 10, 18200, -1000),
    ],
)
def test_option_contract_net_value(
    strike, option, side, premium, quantity, spot, expected
):
    contract = OptionContract(
        strike=strike, option=option, side=side, premium=premium, quantity=quantity
    )
    assert contract.net_value(spot=spot) == expected


def test_payoff_payoff(contracts_list):
    c = contracts_list
    p = OptionPayoff(spot=16000)
    # No contract
    assert p.payoff() == 0
    assert p.payoff(17000) == 0
    # Simple holding
    p.add(c[3])
    assert p.payoff() == 15
    assert p.payoff(16150) == 165
    # Add a future
    p.add(c[4])
    assert p.payoff(16150) == 45
    # Add a call option
    p.add(c[0])
    assert p.payoff(16150) == 95
    # Add 2 put options
    p.add(c[1])
    p.add(c[2])
    assert p.payoff(16150) == 80


def test_option_contract_validate_premium():
    # Raise error when no premium
    with pytest.raises(ValueError):
        contract = OptionContract(strike=16000, option="c", side=1)
    with pytest.raises(ValueError):
        contract = OptionContract(strike=16000, option="p", side=1)
    # Raise no error when futures or holdings
    contract = OptionContract(strike=16000, option="f", side=1)
    contract = OptionContract(strike=16000, option="h", side=1)
