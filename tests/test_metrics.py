import unittest
import pandas as pd

from fastbt.metrics import *


class TestSpread(unittest.TestCase):
    def setUp(self):
        dates = pd.date_range("2016-01-01", "2019-12-31")
        s = pd.Series(index=dates)
        s.loc[:] = 1
        self.s = s

    def test_default(self):
        s = self.s.copy()
        df = spread_test(s)
        answer = pd.DataFrame(
            {
                "num_profit": [4, 16, 48],
                "profit": [1461.0, 1461.0, 1461.0],
                "num_loss": [0, 0, 0],
                "loss": [0.0, 0.0, 0.0],
            },
            index=["Y", "Q", "M"],
        )
        assert answer.equals(df)
