import pytest
import numpy as np
from fastbt.features import *


def test_high_count():
    arr = np.arange(6)
    assert list(high_count(arr)) == [0, 1, 2, 3, 4, 5]


def test_high_count_reversed():
    arr = np.array([5, 4, 3, 2, 1, 0])
    assert np.array_equal(high_count(arr), np.zeros(6, dtype=int))


def test_low_count():
    arr = np.array([5, 4, 3, 2, 1, 0])
    assert list(low_count(arr)) == [0, 1, 2, 3, 4, 5]


def test_low_count_reversed():
    arr = np.arange(6)
    assert np.array_equal(low_count(arr), np.zeros(6, dtype=int))


def test_high_and_low_count():
    arr = np.array([101, 102, 97.4, 91, 96, 102, 106])
    result = np.array([0, 1, 1, 1, 1, 1, 2])
    assert np.array_equal(high_count(arr), result)
    result = np.array([0, 0, 1, 2, 2, 2, 2])
    assert np.array_equal(low_count(arr), result)


def test_last_high():
    arr = np.array([101, 102, 100, 100, 103, 102])
    result = np.array([0, 1, 1, 1, 4, 4])
    assert np.array_equal(last_high(arr), result)
