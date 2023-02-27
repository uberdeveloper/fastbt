from fastbt.options.utils import *
import pytest
import pendulum


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (dict(spot=12344, opt="p"), 12300),
        (dict(spot=248, step=5, opt="put", n=3), 265),
    ],
)
def test_get_atm(test_input, expected):
    assert get_atm(**test_input) == expected


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (dict(spot=12344, opt="c"), 12300),
        (dict(spot=248, opt="call", step=5, n=3), 230),
        (dict(spot=13000, opt="p", n=2), 13200),
    ],
)
def test_get_itm(test_input, expected):
    assert get_itm(**test_input) == expected
