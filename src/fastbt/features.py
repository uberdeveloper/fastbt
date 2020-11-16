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
    for i in np.arange(1, length):
        if values[i] > values[i-1]:
            count+=1
        arr[i] = count
    return arr 



