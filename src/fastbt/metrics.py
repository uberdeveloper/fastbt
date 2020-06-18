"""
This module contains consolidated metrics
"""

import pandas as pd
import numpy as np
try:
    import pyfolio as pf
except ImportError:
    print('pyfolio not installed')


def spread_test(data, periods=['Y', 'Q', 'M']):
    """
    Test whether the returns are spread over the entire period
    or consolidated in a single period
    data
            returns/pnl as series with date as index
    periods
            periods to check as list.
            all valid pandas date offset strings accepted

    returns a dataframe with periods as index and
    profit/loss count and total payoff
    """
    collect = []
    for period in periods:
        rsp = data.resample(period).sum()
        gt = rsp[rsp >= 0]
        lt = rsp[rsp < 0]
        values = (len(gt), gt.sum(), len(lt), lt.sum())
        collect.append(values)
    return pd.DataFrame(collect, index=periods,
                        columns=['num_profit', 'profit', 'num_loss', 'loss'])


def shuffled_drawdown(data, capital=1000):
    """
    Calculate the shuffled drawdown for the given data
    """
    np.random.shuffle(data)
    cum_p = data.cumsum() + capital
    max_p = np.maximum.accumulate(cum_p)
    diff = (cum_p - max_p)/capital
    return diff.min()


def lot_compounding(pnl, lot_size, initial_capital, capital_per_lot):
    """
        Calculate the compounded returns based on lot size
        pnl
                pandas series with daily pnl amount
        lot_size
                lot size; pnl would be multiplied by this lot size since
                pnl is assumed to be for a single quantity
        initial_capital
                initial investment
        capital_per_lot
                capital per lot. Capital at the start of the day
                is divided by this amount to calculate the number of lots
        returns a dataframe with daily capital and the number of lots
        """
    length = len(pnl)
    capital_array = np.zeros(length)
    lots_array = np.zeros(length)
    capital = initial_capital
    lots = round(capital/capital_per_lot)
    capital_array[0] = initial_capital
    lots_array[0] = lots
    profit = pnl.values.ravel()
    for i in range(length-1):
        daily_profit = profit[i] * lot_size * lots
        capital += daily_profit
        lots = round(capital/capital_per_lot)
        capital_array[i+1] = capital
        lots_array[i+1] = lots
    return pd.DataFrame({
        'capital': capital_array,
        'lots': lots_array
    }, index=pnl.index)

class MultiStrategy:
    """
    A class to analyze multiple strategies 
    """
    def __init__(self):
        """
        All initialization goes here
        """
        from fastbt.utils import generate_weights
        self._sources = {}
        self.generate_weights = generate_weights

    def add_source(self, name, data):
        """
        Add a data source as a pandas series
        name
            name of the data source
        data
            a pandas series with date as index
            and profit and loss as values
        """
        self._sources[name] = data
    
    def corr(self, names=[]):
        """
        Create a correlation matrix
        """ 
        pass

    def simulate(self, num=1000):
        """
        Create a simulation with different weights
        """
        pass
