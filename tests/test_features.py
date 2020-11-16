import pytest
import numpy as np
from fastbt.features import *

def test_high_count():
    arr = np.arange(6)
    assert list(high_count(arr)) == [0,1,2,3,4,5]
    
def test_high_count_reversed():
    arr = np.array([5,4,3,2,1,0])
    assert np.array_equal(high_count(arr), np.zeros(6,dtype=int)) 
