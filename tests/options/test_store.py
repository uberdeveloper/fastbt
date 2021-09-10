import pytest
from fastbt.options.store import *
import pendulum


def test_generic_parser():
    name = "AAPL|120|2020-11-15|CE"
    res = generic_parser(name)
    assert res == ("AAPL", 120, pendulum.date(2020, 11, 15), "CE")
