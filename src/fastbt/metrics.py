"""
This module contains consolidated metrics
"""

import pandas as pd
import numpy as np
import os

try:
    pass
except ImportError:
    print("pyfolio not installed")

from fastbt.utils import generate_weights, recursive_merge


def spread_test(data, periods=["Y", "Q", "M"]):
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
    return pd.DataFrame(
        collect, index=periods, columns=["num_profit", "profit", "num_loss", "loss"]
    )


def shuffled_drawdown(data, capital=1000):
    """
    Calculate the shuffled drawdown for the given data
    """
    np.random.shuffle(data)
    cum_p = data.cumsum() + capital
    max_p = np.maximum.accumulate(cum_p)
    diff = (cum_p - max_p) / capital
    return diff.min()


def lot_compounding(pnl, lot_size, initial_capital, capital_per_lot, max_lots=None):
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
    max_lots
        maximum lots after which lot size would not be compounded
    returns a dataframe with daily capital and the number of lots
    """
    length = len(pnl)
    capital_array = np.zeros(length)
    lots_array = np.zeros(length)
    capital = initial_capital
    lots = round(capital / capital_per_lot)
    capital_array[0] = initial_capital
    lots_array[0] = lots
    profit = pnl.values.ravel()
    for i in range(length - 1):
        daily_profit = profit[i] * lot_size * lots
        capital += daily_profit
        lots = round(capital / capital_per_lot)
        if max_lots:
            lots = min(lots, max_lots)
        capital_array[i + 1] = capital
        lots_array[i + 1] = lots
    return pd.DataFrame({"capital": capital_array, "lots": lots_array}, index=pnl.index)


class MultiStrategy:
    """
    A class to analyze multiple strategies
    """

    def __init__(self):
        """
        All initialization goes here
        """
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

    def corr(self, names=[], column="pnl"):
        """
        Create a correlation matrix
        names
            names are the names of data sources to be merged
            by default, all data sources are used
        column
            column name to merge
        """
        keys = self._sources.keys()
        if not (names):
            names = keys
        # Rename columns for better reporting
        collect = []
        for name in names:
            src = self._sources.get(name)
            if src is not None:
                cols = ["date", column]
                tmp = src[cols].rename(columns={column: name})
                collect.append(tmp)
        if len(collect) > 0:
            frame = recursive_merge(collect, on=["date"], how="outer").fillna(0)
            return frame.corr()
        else:
            return []

    def from_directory(self, directory, func=None):
        """
        Add data sources from a directory
        directory
            directory in which the results are stored
        func
            function to be applied after the file is read
        Note
        ----
        This is a helper function to add all portfolio
        results in a directory.
        1) All files are expected to be in csv format
        2) All files should have date and pnl columns
        3) Each file is added as a data source with
        the filename considered the name
        4) Files are not considered case sensitive.
        So, if you have 2 files result.csv and RESULT.csv
        they are considered the same and the data is overwritten
        5) Except csv files, all files in the directory are discarded
        """
        for root, direc, files in os.walk(directory):
            for f in files:
                if f.endswith(".csv"):
                    name = f.split(".")[0]
                    path = os.path.join(root, f)
                    tmp = pd.read_csv(path)
                    if func is not None:
                        tmp = func(tmp)
                    self.add_source(name=name, data=tmp)

    def get_column(self, column="pnl", on="date", how="outer"):
        """
        Get a single column from all the dataframes and merge
        them into a single dataframe
        """
        names = self._sources.keys()
        # Rename columns for better reporting
        collect = []
        for name in names:
            src = self._sources.get(name)
            if src is not None:
                cols = ["date", column]
                tmp = src[cols].rename(columns={column: name})
                collect.append(tmp)
        if len(collect) > 0:
            frame = recursive_merge(collect, on=["date"], how="outer").fillna(0)
            return frame

    def apply(self, column="pnl", func=None):
        """
        Apply a function to each column in the dataframe
        """
        if func is None:
            return pd.DataFrame()
        names = self._sources.keys()
        collect = {}
        for name in names:
            collect[name] = func(self._sources[name][column] / 1000)
        frame = self.get_column(column=column)
        frame2 = frame.mean(axis=1) / 1000
        collect["all"] = func(frame2)
        return collect
