import pytest
from fastbt.options.payoff import *


def test_payoff_defaults():
    p = OptionPayoff()
    assert p.spot == 0
    assert p._options == []
