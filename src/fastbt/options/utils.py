import fastbt.utils as utils
import pendulum
from typing import List, Union

get_itm = utils.get_itm
get_atm = utils.get_atm


def get_expiry(expiries: List[pendulum.DateTime], n: int = 0, sort: bool = True):
    """
    get the nth expiry from the list of expiries
    expiries
        list of sorted expiries
    n
        number of expiry to return
        this is just a simple python list index
    sorted
        if True, the list is sorted and then values are returned. If you already have a sorted list, you can pass False to save on time
    """
    if sort:
        return sorted(expiries)[n]
    else:
        return expiries[n]
