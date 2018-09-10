import pandas as pd
import itertools as it

def multi_args(function, constants, variables, isProduct=False):
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

    By default, this function zips through each of the
    variables but if you need to have the Cartesian
    product, specify those variables in isProduct

    returns a Series with different variables and
    the results
    """
    from functools import partial
    import concurrent.futures

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
            kwds = {a:b for a,b in zip(keys, arg)}
            tasks.append(executor.submit(func, **kwds))
            arg_list.append(arg)
            i += 1
            if i >= 1000:
                print('MAX LIMIT reached')
                break
    result = [task.result() for task in tasks] 
    s = pd.Series(result)
    s.name = 'values'
    s.index = pd.MultiIndex.from_tuples(arg_list, names=keys)
    return s

def stop_loss(price, stop_loss, order='B', tick_size=0.05):
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
    if order == 'B':
        return tick(price * (1 - stop_loss * 0.01), tick_size)
    elif order == 'S':
        return tick(price * (1 + stop_loss * 0.01), tick_size)
    else:
        raise ValueError('order should be either B or S')


def tick(price, tick_size=0.05):
    """
    Rounds a given price to the requested tick
    """
    return round(price / tick_size)*tick_size

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
    data = data.rename(rename, axis='columns')
    for k,v in kwargs.items():
        data[k] = v
    return data
    
if __name__ == "__main__":
    pass

