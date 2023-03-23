import fastbt.utils as utils
import pendulum
from typing import List, Optional

get_itm = utils.get_itm
get_atm = utils.get_atm


def get_expiry(
    expiries: List[pendulum.DateTime], n: int = 1, sort: bool = True
) -> pendulum.DateTime:
    """
    get the nth expiry from the list of expiries
    **1 is the current expiry**
    expiries
        list of sorted expiries
    n
        this is just a simple python list index
    sorted
        if True, the list is sorted and then values are returned.
        If you already have a sorted list, you can pass False to save on time
    Note
    ----
    1) expiries start at 1 (not 0)
    """
    n = n if n < 1 else n - 1
    print("int0")
    if sort:
        return sorted(expiries)[n]
    else:
        return expiries[n]


def get_monthly_expiry(
    expiries: List[pendulum.DateTime], n: int = 1, sort: bool = True
) -> Optional[pendulum.DateTime]:
    """
    get the nth monthly expiry from the list of expiries
    returns the last expiry in the month
    expiries start at 1 (not 0)
    expiries
        list of sorted expiries
    n
        this is just a simple python list index
    sorted
        if True, the list is sorted and then values are returned.
    Note
    ----
    1) returns None if the expiry cannot be found
    """
    if len(expiries) == 1:
        return expiries[0]
    if sort:
        expiries = sorted(expiries)
    i = 1
    prev = expiries[0]
    for prev, date in zip(expiries[:-1], expiries[1:]):
        if prev.month != date.month:
            i += 1
            if i > n:
                return prev
    return date


def get_yearly_expiry(
    expiries: List[pendulum.DateTime], n: int = 1, sort: bool = True
) -> Optional[pendulum.DateTime]:
    """
    get the nth yearly expiry from the list of expiries
    returns the last expiry in the year
    expiries start at 1 (not 0)
    expiries
        list of sorted expiries
    n
        number of expiry to return
    sorted
        if True, the list is sorted and then values are returned.
    """
    if len(expiries) == 1:
        return expiries[0]
    if sort:
        expiries = sorted(expiries)
    i = 1
    prev = expiries[0]
    for prev, date in zip(expiries[:-1], expiries[1:]):
        if prev.year != date.year:
            i += 1
            if i > n:
                return prev
    return date


def get_expiry_by(
    expiries: List[pendulum.DateTime],
    year: int = 0,
    month: int = 0,
    n: int = 1,
    sort: bool = True,
) -> pendulum.DateTime:
    """
    get the nth expiry by year and month
    **1 is the current expiry**
    expiries
        list of sorted expiries
    year
        year to filter, if 0 all years are taken
    month
        month to filter, if 0 all months are taken
    n
        number of expiry to return in the above filter
    sort
        if True, the list is sorted and then values are returned.

    Note
    -----
    1) If month and year are both zero, the nth expiry is returned
    """
    if len(expiries) == 1:
        return expiries[0]
    if sort:
        expiries = sorted(expiries)

    if (month == 0) and (year == 0):
        return get_expiry(expiries, n=n)
    elif month == 0:
        filtered = [expiry for expiry in expiries if expiry.year == year]
    elif year == 0:
        filtered = [expiry for expiry in expiries if expiry.month == month]
    else:
        filtered = [
            expiry
            for expiry in expiries
            if (expiry.year == year and expiry.month == month)
        ]
    n = n if n < 1 else n - 1
    return filtered[n]


def get_expiry_by_days(
    expiries: List[pendulum.DateTime], days: int, sort: bool = True
) -> Optional[pendulum.DateTime]:
    """
    Get the nearest expiry from current date till the given number of days
    expiries
        list of expiries
    days
        number of days to hold the option
    sort
        if True, the list is sorted and then expiry is calculated
    Note
    ----
    1) returns the nearest matching expiry exceeding the given number of days
    2) if the last expiry is less than the given days, no value is returned
    """
    if len(expiries) == 1:
        return expiries[0]
    if sort:
        expiries = sorted(expiries)
    today = pendulum.today(tz="local").date()
    target_date = today.add(days=days)
    if expiries[-1] < target_date:
        # return None if the target date is greater than last expiry
        return None
    for i, expiry in enumerate(expiries):
        if expiry >= target_date:
            return expiry
    return expiry
