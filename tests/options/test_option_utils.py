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
    return sorted(dates)


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


def test_get_yearly_expiry(expiry_dates2):
    dates = expiry_dates2
    assert get_yearly_expiry(dates) == pendulum.date(2021, 12, 31)
    assert get_yearly_expiry(dates, 2) == pendulum.date(2022, 12, 30)
    assert get_yearly_expiry(dates, 4) == pendulum.date(2024, 8, 30)


def test_get_all_single_expiry_date():
    dates = [pendulum.today()]
    assert get_expiry(dates) == get_monthly_expiry(dates) == get_yearly_expiry(dates)


def test_get_expiry_by_no_args(expiry_dates2):
    dates = expiry_dates2
    assert get_expiry_by(dates) == dates[0]
    assert get_expiry_by(dates, n=10) == dates[9]
    assert get_expiry_by(dates, n=101) == dates[100]
    assert get_expiry_by(dates, n=-1) == dates[-1]


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ((2021, 2, 2), (2021, 2, 12)),
        ((2023, 8, 0), (2023, 8, 4)),
        ((2023, 8, 1), (2023, 8, 4)),
        ((2024, 7, -1), (2024, 7, 26)),
        ((2024, 0, 10), (2024, 3, 8)),
        ((0, 0, -7), (2024, 7, 19)),
    ],
)
def test_get_expiry_by(test_input, expected, expiry_dates2):
    dates = expiry_dates2
    assert get_expiry_by(dates, *test_input) == pendulum.date(*expected)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (7, (2021, 1, 8)),
        (100, (2021, 4, 16)),
        (1000, (2023, 9, 29)),
    ],
)
def test_get_expiry_by_days(test_input, expected, expiry_dates2):
    dates = expiry_dates2
    known = pendulum.datetime(2021, 1, 1)
    with pendulum.test(known):
        assert get_expiry_by_days(dates, test_input) == pendulum.date(*expected)


def test_get_expiry_by_dates_no_matching_date(expiry_dates2):
    assert get_expiry_by_days(expiry_dates2, 10000) is None
