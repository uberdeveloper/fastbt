"""
Features for machine learning and other analysis
All features are optimized with numba for speed
"""

import numpy as np
from numba import njit


@njit
def high_count(values):
    """
    Given a list of values, return the number of
    times high is broken
    >>> arr = np.array([11,12,9,8,13])
    >>> list(high_count(arr))
    [0, 1, 1, 1, 2]
    """
    length = len(values)
    arr = np.zeros(length, dtype=np.int16)
    count = 0
    max_val = values[0]
    for i in np.arange(1, length):
        if values[i] > max_val:
            max_val = values[i]
            count += 1
        arr[i] = count
    return arr


@njit
def low_count(values):
    """
    Given a list of values, return the number of
    times low is broken
    >>> arr = np.array([13,14,12,11,9,10])
    >>> list(low_count(arr))
    [0, 0, 1, 2, 3, 3]
    """
    length = len(values)
    arr = np.zeros(length, dtype=np.int16)
    count = 0
    min_val = values[0]
    for i in np.arange(1, length):
        if values[i] < min_val:
            min_val = values[i]
            count += 1
        arr[i] = count
    return arr


@njit
def last_high(values):
    """
    Given a list of values, return an array with
    the index of the corresponding last highs
    Note
    ----
    index starts at zero
    >>> arr = np.array([12,14,11,12,13,18])
    >>> list(last_high(arr))
    [0, 1, 1, 1, 1, 5]
    """
    length = len(values)
    arr = np.zeros(length, dtype=np.int32)
    max_val = values[0]
    counter = 0
    for i in np.arange(1, length):
        if values[i] > max_val:
            max_val = values[i]
            counter = i
        arr[i] = counter
    return arr
