import pytest
import numpy as np
from fastbt.simulation import *
from pandas.testing import assert_frame_equal

test_data = (
    pd.read_csv("tests/data/index.csv", parse_dates=["date"])
    .set_index("date")
    .sort_index()
)


def test_walk_forward_simple():
    expected = pd.read_csv("tests/data/is_pret.csv", parse_dates=["date"])
    result = walk_forward(test_data, "Y", ["is_pret"], "ret", sum)
    del result["_period"]
    assert len(result) == len(expected)
    assert_frame_equal(expected, result)
