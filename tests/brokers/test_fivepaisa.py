import pytest
from unittest.mock import Mock,patch,call

from fastbt.brokers.fivepaisa import *
import requests
import json

contracts = {
        'NSE:SBIN': 3045,
        'NFO:SBT': 5316
        }

def test_get_instrument_token():
    token = get_instrument_token(contracts, 'NSE', 'SBIN')
    assert token == 3045
    token = get_instrument_token(contracts, 'NFO', 'SBT')
    assert token == 5316
    token = get_instrument_token(contracts, 'NFO', 'ABCD')
    assert token is None
    
def test_broker_get_instrument_token():
    broker = FivePaisa('a','b','c')
    broker.contracts = contracts
    assert broker._get_instrument_token(symbol='SBIN') == 3045

def test_broker_get_instrument_token_override_contracts():
    broker = FivePaisa('a','b','c')
    assert broker._get_instrument_token(symbol='SBIN', contracts=contracts) == 3045

