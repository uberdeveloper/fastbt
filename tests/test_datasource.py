import unittest
import pandas as pd
import numpy as np
import context

from fastbt.datasource import DataSource
import talib


class TestDataSource(unittest.TestCase):
    def setUp(self):
        df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"])
        self.ds = DataSource(data=df)

    def test_data(self):
        self.assertEqual(self.ds.data.iloc[20, 1], "five")
        self.assertEqual(self.ds.data.iloc[14, 3], 112)
        self.assertEqual(self.ds.data.iloc[24, 7], 10.54)

    def test_data_without_sort(self):
        df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"])
        self.ds = DataSource(data=df, sort=False)
        self.assertEqual(self.ds.data.iloc[9, 4], 999)
        self.assertEqual(self.ds.data.iloc[24, 6], 41688)
        self.assertEqual(self.ds.data.at[4, "close"], 10.6)

    def test_initialize_case(self):
        df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"])
        df.columns = [x.upper() for x in df.columns]
        self.assertEqual(df.columns[0], "TIMESTAMP")
        self.ds = DataSource(data=df)
        self.assertEqual(self.ds.data.columns[0], "timestamp")

    def test_initialize_column_rename(self):
        df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"])
        df.columns = [
            "TS",
            "TRADINGSYMBOL",
            "OPEN",
            "HIGH",
            "LOW",
            "CLOSE",
            "VOLUME",
            "PREVCLOSE",
        ]
        self.ds = DataSource(data=df, timestamp="TS", symbol="TRADINGSYMBOL")
        self.assertEqual(self.ds.data.columns[0], "timestamp")
        self.assertEqual(self.ds.data.columns[1], "symbol")

    def test_add_lag(self):
        length = len(self.ds.data)
        idx = pd.IndexSlice
        self.ds.add_lag(on="close")
        self.ds.add_lag(on="volume", period=2)
        d = self.ds.data.set_index(["timestamp", "symbol"])
        self.assertEqual(d.at[idx["2018-01-04", "one"], "lag_close_1"], 11)
        self.assertEqual(d.at[idx["2018-01-06", "six"], "lag_volume_2"], 86014)
        self.assertEqual(len(self.ds.data.columns), 10)
        self.assertEqual(len(self.ds.data), length)

    def test_add_lag_column_rename(self):
        idx = pd.IndexSlice
        self.ds.add_lag(on="close")
        self.ds.add_lag(on="close", col_name="some_col")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        self.assertEqual(d.at[idx["2018-01-04", "one"], "lag_close_1"], 11)
        self.assertEqual(d.at[idx["2018-01-04", "one"], "some_col"], 11)
        self.assertEqual(d.at[idx["2018-01-05", "three"], "some_col"], 109)

    def test_add_pct_change(self):
        idx = pd.IndexSlice
        self.ds.add_pct_change(on="close")
        self.ds.add_pct_change(on="close", period=2)
        self.ds.add_pct_change(on="close", period=2, col_name="new_col")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-05", "three"], "chg_close_1"]), -0.07)
        self.assertEqual(R(d.at[idx["2018-01-06", "five"], "chg_close_1"]), 0.17)
        self.assertEqual(R(d.at[idx["2018-01-05", "four"], "chg_close_2"]), 0.05)
        self.assertEqual(R(d.at[idx["2018-01-05", "four"], "new_col"]), 0.05)
        self.assertEqual(R(d.at[idx["2018-01-03", "six"], "new_col"]), -0.1)
        self.assertEqual(pd.isna(d.at[idx["2018-01-02", "one"], "new_col"]), True)
        self.assertEqual(len(self.ds.data.columns), 11)

    def test_add_pct_change_lag(self):
        idx = pd.IndexSlice
        self.ds.add_pct_change(on="close", period=2, lag=1)
        self.ds.add_pct_change(on="close", period=1, lag=2)
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-04", "four"], "chg_close_2"]), 0.09)
        self.assertEqual(R(d.at[idx["2018-01-04", "four"], "chg_close_1"]), 0.01)
        self.assertEqual(R(d.at[idx["2018-01-06", "three"], "chg_close_1"]), -0.01)

    def test_add_pct_change_lag_col_name(self):
        idx = pd.IndexSlice
        self.ds.add_pct_change(on="high", period=2, lag=1)
        self.ds.add_pct_change(on="close", period=1, lag=2, col_name="lagged_2")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-05", "six"], "chg_high_2"]), -0.04)
        self.assertEqual(R(d.at[idx["2018-01-04", "four"], "lagged_2"]), 0.01)

    def test_formula_add_col_name(self):
        idx = pd.IndexSlice
        self.ds.add_formula("open+close", "new_col")
        self.ds.add_formula("volume/close", "new_col_2")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-04", "four"], "new_col"]), 336)
        self.assertEqual(R(d.at[idx["2018-01-06", "one"], "new_col_2"]), 77755.77)

    def test_formula_case_insensitive(self):
        idx = pd.IndexSlice
        self.ds.add_formula("OPEN+CLOSE", "new_col")
        self.ds.add_formula("volume/close", "NEW_COL_2")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-04", "four"], "new_col"]), 336)
        self.assertEqual(R(d.at[idx["2018-01-06", "one"], "new_col_2"]), 77755.77)

    def test_formula_calculated_column(self):
        idx = pd.IndexSlice
        self.ds.add_formula("(open+close)*100", "new_col_1")
        self.ds.add_formula("volume/100", "new_col_2")
        self.ds.add_formula("new_col_1+new_col_2", "new_col_3")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(R(d.at[idx["2018-01-06", "one"], "new_col_3"]), 10190.6)
        self.assertEqual(R(d.at[idx["2018-01-05", "two"], "new_col_3"]), 200389.97)

    def test_rolling_simple(self):
        from pandas import isna

        q = 'symbol == "one"'
        df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"]).query(q)
        df["r2"] = df["close"].rolling(2).mean()
        self.ds.add_rolling(2, col_name="r2")
        df2 = self.ds.data.query(q)
        print("RESULT", df["r2"], df2["r2"])
        for a, b in zip(df["r2"], df2["r2"]):
            if not (isna(a)):
                assert a == b

    def test_rolling_values(self):
        idx = pd.IndexSlice
        self.ds.add_rolling(4, on="volume", function="max")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        R = lambda x: round(x, 2)
        self.assertEqual(d.at[idx["2018-01-05", "five"], "rol_max_volume_4"], 971704)
        self.assertEqual(d.at[idx["2018-01-05", "six"], "rol_max_volume_4"], 195539)
        self.assertEqual(d.at[idx["2018-01-04", "three"], "rol_max_volume_4"], 433733)
        # Adding lag and testing
        self.ds.add_rolling(4, on="volume", function="max", lag=1)
        d = self.ds.data.set_index(["timestamp", "symbol"])
        self.assertEqual(d.at[idx["2018-01-06", "five"], "rol_max_volume_4"], 971704)
        self.assertEqual(d.at[idx["2018-01-06", "six"], "rol_max_volume_4"], 195539)
        self.assertEqual(d.at[idx["2018-01-05", "three"], "rol_max_volume_4"], 433733)
        # Testing for 2 lags and column name
        self.ds.add_rolling(4, on="volume", function="max", lag=2, col_name="check")
        d = self.ds.data.set_index(["timestamp", "symbol"])
        self.assertEqual(d.at[idx["2018-01-06", "three"], "check"], 433733)

    def test_batch(self):
        length = len(self.ds.data)
        batch = [
            {"P": {"on": "close", "period": 1, "lag": 1}},
            {"L": {"on": "volume", "period": 1}},
            {"F": {"formula": "(open+close)/2", "col_name": "AvgPrice"}},
            {"I": {"indicator": "SMA", "period": 3, "lag": 1, "col_name": "SMA3"}},
            {"F": {"formula": "avgprice + sma3", "col_name": "final"}},
            {"R": {"window": 3, "function": "mean"}},
        ]
        d = self.ds.batch_process(batch).set_index(["timestamp", "symbol"])
        self.assertEqual(len(d.columns), 12)
        self.assertEqual(len(self.ds.data.columns), 14)
        self.assertEqual(len(self.ds.data), length)

    def test_raise_error_if_not_dataframe(self):
        pass


def test_rolling_zscore():
    np.random.seed(100)
    df = pd.DataFrame(np.random.randn(100, 4), columns=["open", "high", "low", "close"])
    df["symbol"] = list("ABCD") * 25
    dates = list(pd.date_range(end="2018-04-25", periods=25)) * 4
    df["timestamp"] = dates
    from fastbt.datasource import DataSource

    ds = DataSource(df)
    ds.add_rolling(on="close", window=5, function="zscore")
    assert ds.data.query('symbol=="A"').iloc[8]["rol_zscore_close_5"].round(2) == 0.12
    assert ds.data.query('symbol=="B"').iloc[-7]["rol_zscore_close_5"].round(2) == 0.17
    assert ds.data.query('symbol=="C"').iloc[-6]["rol_zscore_close_5"].round(2) == -0.48


class TestDataSourceReindex(unittest.TestCase):
    def setUp(self):
        df = pd.DataFrame(
            np.arange(24).reshape(6, 4), columns=["open", "high", "low", "close"]
        )
        df["symbol"] = list("ABCABA")
        df["timestamp"] = [1, 1, 1, 2, 3, 3]
        self.df = df

    def test_reindex(self):
        ds = DataSource(self.df)
        ds.reindex([1, 2, 3])
        assert len(ds.data) == 9
        # Check values
        assert ds.data.set_index(["symbol", "timestamp"]).at[("A", 1), "open"] == 0
        assert ds.data.set_index(["symbol", "timestamp"]).at[("B", 2), "close"] == 7
        assert ds.data.set_index(["symbol", "timestamp"]).at[("C", 3), "high"] == 9
        ds.reindex([1, 2, 3, 4])
        assert len(ds.data) == 12

    def test_reindex_different_fills(self):
        ds = DataSource(self.df)
        ds.reindex([1, 2, 3], method=None)
        print(ds.data)
        assert pd.isnull(
            ds.data.set_index(["symbol", "timestamp"]).at[("C", 3), "high"]
        )
        ds = DataSource(self.df)
        ds.reindex([1, 2, 3, 4], method="bfill")
        assert ds.data.set_index(["symbol", "timestamp"]).at[("B", 2), "close"] == 19


class TestDataSourceTALIB(unittest.TestCase):

    """
    Test TALIB indicators
    """

    def setUp(self):
        self.df = pd.read_csv("tests/data/sample.csv", parse_dates=["timestamp"])

    def test_single_symbol(self):
        df = self.df.query('symbol=="one"')
        ds = DataSource(df)
        ds.add_indicator("SMA", period=3, col_name="sma")
        assert len(ds.data) == 6

        sma = talib.SMA(df.close.values, timeperiod=3)
        # If both are equal, there should be no differences
        assert (ds.data.sma - sma).sum() == 0
