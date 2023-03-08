from fastbt.options.utils import *
import pytest
import pendulum
import random


@pytest.fixture
def expiry_dates():
    date = pendulum.date(2021, 1, 31)
    dates = []
    for i in range(18):
        dates.append(date.add(months=i))
    return dates


@pytest.fixture
def expiry_dates2():
    """
    contains a lot of dates
    """
    start = pendulum.date(2021, 1, 1)
    end = pendulum.date(2024, 8, 31)
    period = pendulum.period(start, end)
    dates = []
    for p in period.range("weeks"):
        dates.append(p)
    return dates


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


def test_get_expiry(expiry_dates):
    assert get_expiry(expiry_dates, sort=False) == pendulum.date(2021, 1, 31)
    assert get_expiry(expiry_dates, 3, sort=False) == pendulum.date(2021, 3, 31)
    assert get_expiry(expiry_dates, -1, sort=False) == pendulum.date(2022, 6, 30)


def test_get_expiry_unsorted(expiry_dates):
    dates = expiry_dates[:]
    random.shuffle(dates)
    # Make sure the first date is not the least expiry
    assert dates[0] != pendulum.date(2021, 1, 31)
    assert get_expiry(dates) == pendulum.date(2021, 1, 31)
    assert get_expiry(dates, 2) == pendulum.date(2021, 2, 28)
    assert get_expiry(dates, -1) == pendulum.date(2022, 6, 30)


def test_get_monthly_expiry(expiry_dates2):
    dates = expiry_dates2
    assert get_monthly_expiry(dates) == pendulum.date(2021, 1, 29)
    assert get_monthly_expiry(dates, 5) == pendulum.date(2021, 5, 28)
    assert get_monthly_expiry(dates, 27) == pendulum.date(2023, 3, 31)
