import pandas as pd
import numpy as np
import itertools as it
import functools as ft
from numpy import arange
from typing import List, Dict, Any
import urllib.parse as parse

try:
    from numba import njit
except ImportError:
    print("Install numba")


def multi_args(function, constants, variables, isProduct=False, maxLimit=None):
    """
    Run a function on different parameters and
    aggregate results
    function
        function to be parametrized
    constants
        arguments that would remain constant
        throughtout all the scenarios
        dictionary with key being argument name
        and value being the argument value
    variables
        arguments that need to be varied
        dictionary with key being argument name
        and value being list of argument values
        to substitute
    isProduct
        list of variables for which all combinations
        are to be tried out.
    maxLimit
        Maximum number of simulations to be run
        before terminating. Useful in case of long
        running simulations.
        default 1000

    By default, this function zips through each of the
    variables but if you need to have the Cartesian
    product, specify those variables in isProduct.

    returns a Series with different variables and
    the results
    """
    from functools import partial
    import concurrent.futures

    if maxLimit:
        MAX_LIMIT = maxLimit
    else:
        MAX_LIMIT = 1000

    func = partial(function, **constants)
    arg_list = []
    if isProduct:
        args = it.product(*variables.values())
    else:
        args = zip(*variables.values())
    keys = variables.keys()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        tasks = []
        for i, arg in enumerate(args):
            kwds = {a: b for a, b in zip(keys, arg)}
            tasks.append(executor.submit(func, **kwds))
            arg_list.append(arg)
            i += 1
            if i >= MAX_LIMIT:
                print("MAX LIMIT reached", MAX_LIMIT)
                break
    result = [task.result() for task in tasks]
    s = pd.Series(result)
    s.name = "values"
    s.index = pd.MultiIndex.from_tuples(arg_list, names=keys)
    return s


def stop_loss(price, stop_loss, order="B", tick_size=0.05):
    """
    Return the stop loss for the order
    price
        price from which stop loss is to be calculated
    stop_loss
        stop loss percentage from price
    order
        the original order type - B for Buy and S for Sell
        If the original order is buy, then a sell stop
        loss is generated and vice-versa
    tick_size
        tick_size to be rounded off
    >>> stop_loss(100, 3)
    >>> 97

    Notes
    ------
    * passing a negative value may throw unexpected results
    * raises ValueError if order is other than B or S

    """
    if order == "B":
        return tick(price * (1 - stop_loss * 0.01), tick_size)
    elif order == "S":
        return tick(price * (1 + stop_loss * 0.01), tick_size)
    else:
        raise ValueError("order should be either B or S")


def tick(price, tick_size=0.05):
    """
    Rounds a given price to the requested tick
    """
    return round(price / tick_size) * tick_size


def create_orders(data, rename, **kwargs):
    """
    create an orders dataframe from an existing dataframe
    by renaming columns and providing additional columns
    data
        dataframe
    rename
        columns to be renamed as dictionary
    kwargs
        key value pairs with key being column names
        and values being dataframe values
    """
    data = data.rename(rename, axis="columns")
    for k, v in kwargs.items():
        data[k] = v
    return data


def recursive_merge(dfs, on=None, how="inner", columns={}):
    """
    Recursively merge all dataframes in the given list

    Given a list of dataframes, merge them based on index or columns.
    By default, dataframes are merged on index. Specify the **on**
    argument to merge by columns. The "on" columns should be available
    in all the dataframes

    Parameters
    -----------
    dfs
        list of dataframes
    on
        columns on which the dataframes are to be merged.
        By default, merge is done on index
    how
        how to apply the merge
        {'left', 'right', 'outer', 'inner'}, default 'inner'.
        Same as pandas merge
    columns
        To return only specific columns from specific dataframes,
        pass them as a dictionary with key being the index of the
        dataframe in the list and value being the list of columns
        to merge. **your keys should be string**
        See examples for more details
        >>> recursive_merge(dfs, columns = {'1': ['one', 'two']})
        Fetch only the columns one and two from the second dataframe
    """
    data = dfs[0]
    for i, d in enumerate(dfs[1:], 1):
        if columns.get(str(i)):
            cols = list(columns.get(str(i)))
            cols.extend(on)
        else:
            cols = d.columns

        if on is None:
            data = data.merge(d[cols], how=how, left_index=True, right_index=True)
        else:
            data = data.merge(d[cols], how=how, on=on)
    return data


def get_nearest_option(spot, n=1, opt="C", step=100):
    """
    Given a spot price, calculate the nearest options
    spot
        spot price of the instrument
    n
        number of nearest option prices
    opt
        call or put option. 'C' for call and 'P' for put
    step
        step size of the option price
    returns a list of options
    >>> get_nearest_option(23457, 2)
    >>> [23400, 23500]
    >>> get_nearest_option(23457, 2, 'P')
    >>> [23400, 23300]
    All calculations are based on in the money option. So,
    get_nearest_option(24499) would return 24400
    """
    in_money = int(spot / step) * step
    option_prices = []
    for i in range(n):
        if opt == "C":
            strike = in_money + step * i
            option_prices.append(strike)
        elif opt == "P":
            strike = in_money - step * i
            option_prices.append(strike)
        else:
            print("Option type not recognized; Check the opt argument")
    return option_prices


def calendar(
    start,
    end,
    holidays=None,
    alldays=False,
    start_time=None,
    end_time=None,
    freq="D",
    **kwargs,
):
    """
    Generate a calendar removing the list of
    given holidays.
    Provide date arguments as strings in the
    format **YYYY-MM-DD**
    start
        start date of the period
    end
        end date of the period
    holidays
        list of holidays as strings
    alldays
        True/False
        True to generate dates for all days
        including weekends. default: False
    start_time
        start time for each day as string
    end_time
        end time for each day as string
    freq
        frequency of the calendar
    kwargs
        kwargs to the pandas date range function

    Note
    -----
    1) This function is slow, especially when generating
    timestamps. So, use them only once at the start
    of your program for better performance
    2) This function generates calendar only for
    business days. To use all the available days,
    se the alldays argument to True

    """
    if alldays:
        dfunc = ft.partial(pd.date_range, freq="D", **kwargs)
    else:
        dfunc = ft.partial(pd.bdate_range, freq="B", **kwargs)

    dates = list(dfunc(start=start, end=end))
    if holidays:
        holidays = [pd.to_datetime(dt) for dt in holidays]
        for hol in holidays:
            dates.remove(hol)

    # Initialize times
    if start_time or end_time:
        if not (start_time):
            start_time = "00:00:00"
        if not (end_time):
            end_time = "23:59:59"
        timestamps = []
        fmt = "{:%Y%m%d} {}"
        for d in dates:
            start_ts = fmt.format(d, start_time)
            end_ts = fmt.format(d, end_time)
            ts = pd.date_range(start=start_ts, end=end_ts, freq=freq, **kwargs)
            timestamps.extend(ts)
        return timestamps
    else:
        return dates


def get_ohlc_intraday(
    data, start_time, end_time, date_col=None, col_mappings=None, sort=False
):
    """
    Get ohlc for a specific period in a day for all days
    for all the symbols.
    data
        dataframe with symbol, timestamp, date, open, high, low, close columns.
        The timestamp and date columns are assumed to be of pandas datetime type.
        Each row represents data for a single stock at a specified period of time
        If you have different column names, use the col_mappings argument
        to rename the columns
    start_time
        start time for each day
    end_time
        end time for each day
    date_col
        date column to aggregate; this is in addition to time column.
        If no date column is specified, a date column is created.
    col_mappings
        column mappings as a dictionary
        (Eg.) if the symbol column is named as assetName and timestamp
        as ts, then pass rename={'assetName': 'symbol', 'ts': 'timestamp'}
    sort
        Whether the data is sorted by timestamp.
        If True, data is not sorted else data is sorted

    returns
        a dataframe with symbol, date, open, high, low and close columns

    Note
    -----
    To speed up computation
        1) If the data is already sorted, pass sort=True
        2) If date column is already available, then pass date_col=column_name
    Timestamp and date are assumed to be pandas datetime
    """
    if col_mappings:
        data = data.rename(col_mappings, axis="columns")
    if not (sort):
        data = data.sort_values(by="timestamp")
    if not (date_col):
        data["date"] = data["timestamp"].dt.date
        date_col = "date"
    data = data.set_index("timestamp")

    def calculate_ohlc(df):
        """
        Internal function to calculate OHLC
        """

        date = df.iloc[0].at[date_col].strftime("%Y-%m-%d")
        fmt = "{date} {time}"  # date time format
        s = fmt.format(date=date, time=start_time)
        e = fmt.format(date=date, time=end_time)
        temp = df.loc[s:e]
        agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
        return temp.groupby("symbol").agg(agg)

    return data.groupby([date_col]).apply(calculate_ohlc)


def get_expanding_ohlc(data, freq, col_mappings=None):
    """
    Given a dataframe with OHLC, timestamp and symbol columns
    return a OHLC dataframe with open price, expanding high,
    expanding low and close prices
    data
        dataframe with OHLC, timestamp and symbol columns
    freq
        frequency by which the data is to be resampled.
        A pandas frequency string
    col_mappings
        column mappings as a dictionary
        (Eg.) if the symbol column is named as assetName and timestamp
        as ts, then pass rename={'assetName': 'symbol', 'ts': 'timestamp'}
    Note
    -----
    The returned dataframe has the same length and index of the
    original dataframe. The resampling is done only to calculate the
    expanding high, low prices
    """
    if col_mappings:
        data = data.rename(col_mappings, axis="columns")

    def calculate_ohlc(df):
        temp = pd.DataFrame(
            {"high": df["high"].expanding().max(), "low": df["low"].expanding().min()}
        )
        temp["close"] = df["close"]
        temp["open"] = df["open"].iloc[0]
        return temp

    cols = ["open", "high", "low", "close"]  # for sorting return value
    return data.resample(freq).apply(calculate_ohlc)[cols]


def generate_index(index, changes, dates=None):
    """
    index
        list of symbols that make up the latest index
    changes
        changes to the index as a dataframe.
        The dataframe should have the following three columns
        in the following order
         1. date - date of change
         2. symbol - security involving the change
         3. flag - True/False indicating inclusion/exclusion into the index
         True indicates inclusion and False exclusion
    dates
        list of dates to generate index
    returns a dataframe with symbols for each date

    Note
    -----
    * The changes dataframe is expected in the exact order.
    Any other columns are discarded
    """
    collect = {}
    idx = index[:]
    changes = changes.sort_values(by="date", ascending=False)
    dates = [x for x in reversed(dates)]
    uniq_dates = [x for x in changes.date.unique()]
    for d in dates:
        if d in uniq_dates:
            formula = f'date=="{d}"'
            chx = changes.query(formula)
            for i, row in chx.iterrows():
                try:
                    if not (row["flag"]):
                        idx.append(row["symbol"])
                    else:
                        idx.remove(row["symbol"])
                except Exception as e:
                    print(e, d, row)
        collect[d] = idx[:]
    frame = pd.melt(pd.DataFrame.from_dict(collect))
    frame.columns = ["date", "symbol"]
    return frame.sort_values(by="date").reset_index(drop=True)


def custom_index(data, on, window=30, function="median", num=30, sort_mode=False):
    """
    Generate a custom index
    data
        dataframe with symbol and timestamp columns
    on
        column on which the index is to be generated
    window
        look back window
    function
        function to be applied
    out
        number of stocks to pick each day
    sort_mode
        whether to pick top stocks or bottom stocks
    """
    from fastbt.datasource import DataSource

    ds = DataSource(data)
    ds.add_rolling(
        on=on, window=window, function=function, lag=1, col_name="custom_index"
    )
    grouped = ds.data.groupby("timestamp")
    if sort_mode:
        return grouped.apply(
            lambda x: x.sort_values(by="custom_index").head(num)
        ).reset_index(drop=True)
    else:
        return grouped.apply(
            lambda x: x.sort_values(by="custom_index").tail(num)
        ).reset_index(drop=True)


@njit
def streak(values):
    """
    Calculates the continuous streak of a variable.
    Given an array of discrete values, calculate the
    continuous streak of each value.
    values
        numpy array of values
    Note
    -----
    1) Pass numpy arrays for faster computation. In case of pandas series,
    pass series.values
    2) Calculates the streak based on number of consecutive
    values that appear in the array
    """
    l = len(values)
    arr = np.ones(l, dtype=np.int32)
    cnt = 1
    for i in arange(1, l):
        if values[i] == values[i - 1]:
            cnt += 1
        else:
            cnt = 1
        arr[i] = cnt
    return arr


@njit
def trend(up, down, threshold=2 / 3):
    """
    up
        numpy array
        up values as the difference between open and high
    down
        numpy array
        down values as the difference between open and low
    threshold
        threshold considered as a valid trend
    """
    total = up + down
    up_vals = up / total
    down_vals = down / total
    length = len(total)
    arr = np.zeros(length)
    for i in np.arange(length):
        if up_vals[i] > threshold:
            arr[i] = 1
        elif down_vals[i] > threshold:
            arr[i] = -1
        else:
            arr[i] = 0
    return arr


def generate_weights(n=2, size=1):
    """
    Generate random weights that sum to one; uses the dirichlet
    distribution to generate weights
    """
    return np.random.dirichlet(np.ones(n), size)


def stop_loss_step_decimal(
    price: float, side: str = "B", dec: float = 0.45, step: int = 2
) -> float:
    """
    Truncates down the stop loss value to the desired step
    and adds the given decimal
    price
        stop loss price
    side
        side to place order, the actual stop loss side
        B for BUY, S for SELL
    dec
        fixed decimal to be added
    step
        step size to determine stop
    Note
    ----
    1. Step object is always a positive number
    2. Side is the actual stop loss side you are placing the order
    """
    step = abs(step)
    m = int(price / step)
    val = (m + 1) * step if side == "S" else (m * step) - 1
    val = val + 1 - dec if side == "S" else val + dec
    return val


def get_nearest_premium(
    premium: float,
    instrument_map: List[Dict],
    symbol: str = "symbol",
    last_price: str = "last_price",
) -> str:
    """
    Get the symbol with the nearest premium from the given list of instruments
    premium
        premium to search
    instrument map
        instrument map as a list with data as dictionaries
    symbol
        symbol key in instrument map
    last_price
        last_price key in instrument map
    Note
    ----
    1. nearest premium is calculated on the basis of absolute difference
    """
    diff = 1e10
    latest_symbol = None
    for inst in instrument_map:
        price = inst.get(last_price)
        d = abs(premium - price)
        if d < diff:
            diff = d
            latest_symbol = inst.get(symbol)
    return latest_symbol


def stockmock_parser(url: str) -> Dict[str, Any]:
    """
    A parser for stock mock url strategies
    """

    def parse_positions(position):
        dct = {}
        args = [p.split("_") for p in position]
        dct["instrument"] = args[0][0]
        dct["atm"] = int(args[1][0])
        dct["side"] = args[1][1]
        dct["opt"] = args[1][2]
        dct["quantity"] = int(args[1][3])
        for arg in args[2:]:
            key = arg[0]
            if key == "SLP":
                dct["stop_loss"] = arg[1]
            elif key == "TPP":
                dct["target"] = arg[1]
            elif key == "CW":
                dct["expiry"] = "weekly"
            elif key == "CM":
                dct["expiry"] = "monthly"
            elif key == "TSLP":
                dct["trailing_stop"] = arg[1]
                dct["trailing_profit"] = arg[1]
            elif key == "WP":
                dct["wait_premium"] = arg[1]
        # Force conversion of numbers
        for k, v in dct.items():
            try:
                dct[k] = float(v)
            except Exception:
                pass
        return dct

    url_params = parse.parse_qsl(url)
    params = {}
    for k, v in url_params:
        if k == "et":
            s, e = v.split(",")
            params["start_time"] = s
            params["end_time"] = e
        elif k == "s":
            params["strategy"] = v

    positions = url_params[0][1].split(",")
    positions = [x.split("::") for x in positions]
    pos = [parse_positions(p) for p in positions]
    params["positions"] = pos
    return params


def get_atm(spot: float, opt: str = "c", step: float = 100.0, n=0) -> float:
    """
    Get the at the money option; the most nearest option.
    This is common for both put and call options
    spot
        spot price of the underlying
    opt
        c for call option and p for put option
    step
        option price step
    n
        strikes above or below atm based on the step and type of option
    """
    opt = opt.lower()[0]
    sign = 1 if opt == "p" else -1
    strike = round(spot / step) * step
    return strike + n * sign * step


def get_itm(spot: float, opt: str, step: float = 100.0, n=0) -> float:
    """
    Get in the money option
    spot
        spot price of the underlying
    opt
        put or call - only the first character is taken
    step
        option price step
    Note
    ----
    1) If opt is neither call or put, 0 is returned
    """
    opt = opt.lower()[0]
    sign = 1 if opt == "p" else -1
    if spot % step == 0:
        return spot + n * sign * step
    elif opt == "c":
        strike = int(spot / step) * step
        return strike + n * sign * step
    elif opt == "p":
        strike = (int(spot / step) * step) + step
        return strike + n * sign * step
    else:
        return 0.0
