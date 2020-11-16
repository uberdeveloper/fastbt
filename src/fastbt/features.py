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
    """
    length = len(values)
    arr = np.zeros(length, dtype=np.int16)
    count = 0
    max_val = values[0]
    for i in np.arange(1, length):
        if values[i] > max_val:
            max_val = values[i]
            count+=1
        arr[i] = count
    return arr 

@njit
def low_count(values):
    """
    Given a list of values, return the number of 
    times low is broken
    """
    length = len(values)
    arr = np.zeros(length, dtype=np.int16)
    count = 0
    min_val = values[0]
    for i in np.arange(1, length):
        if values[i] < min_val:
            min_val = values[i]
            count+=1
        arr[i] = count
    return arr 

