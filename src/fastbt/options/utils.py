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
    year=int,
    month=int,
    n: int = 1,
    sort: bool = True,
) -> pendulum.DateTime:
    """
    get the nth expiry by year and month
    **1 is the current expiry**
    expiries
        list of sorted expiries
    year
        year to filter
    month
        month to filter
    n
        number of expiry to return in the above filter
    sorted
        if True, the list is sorted and then values are returned.
    """
    n = n if n < 1 else n - 1
    if len(expiries) == 1:
        return expiries[0]
    if sort:
        expiries = sorted(expiries)
    filtered = [
        expiry for expiry in expiries if (expiry.year == year and expiry.month == month)
    ]
    return filtered[n]
