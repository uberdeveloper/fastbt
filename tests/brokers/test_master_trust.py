import pytest
from unittest.mock import Mock,patch,call

from fastbt.brokers.master_trust import *
import requests
import json

contracts_data = {
        'NSE': [
            {"trading_symbol":"SBIN-EQ","symbol":"SBIN","exchange_code":1,"exchange":"NSE","company":"STATE BANK OF INDIA","code":"3045"},
            {"trading_symbol":"SBT-EQ","symbol":"SBT","exchange_code":1,"exchange":"NSE","company":"STATE BANK OF TRAVANCORE","code":"5316"}],
        'NSE-OTH': 
        [{"trading_symbol":"1018GS2026-GS","symbol":"1018GS2026 GS","exchange_code":1,"exchange":"NSE","company":"GOI LOAN 10.18% 2026","code":"6833"}]
        }


@patch('requests.get')
def test_fetch_all_contracts(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    result = {
            'NSE:SBIN-EQ': '3045',
            'NSE:SBT-EQ': '5316',
            'NSE:1018GS2026-GS': '6833'
            }
    contracts = fetch_all_contracts(exchanges=['NSE'])
    assert result == contracts


@patch('requests.get')
def test_fetch_all_contracts_multiple_exchanges(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    result = {
            'NSE:SBIN-EQ': '3045',
            'NSE:SBT-EQ': '5316',
            'NSE:1018GS2026-GS': '6833',
            'NFO:SBIN-EQ': '3045',
            'NFO:SBT-EQ': '5316',
            'NFO:1018GS2026-GS': '6833'
            }
    contracts = fetch_all_contracts()
    assert result == contracts

@patch('requests.get')
def test_get_instrument_token(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    contracts = fetch_all_contracts()
    token = get_instrument_token(contracts, 'NSE', 'SBIN-EQ')
    assert token == '3045'
    token = get_instrument_token(contracts, 'NFO', 'SBT-EQ')
    assert token == '5316'

def test_broker_get_instrument_token():
    broker = MasterTrust('a','b','c','d','e') # dummy arguments
    broker.contracts = contracts_data
    broker._get_instrument_token(symbol='SBIN-EQ') == '3045'

def test_broker_get_instrument_token_override_contracts():
    broker = MasterTrust('a','b','c','d','e') # dummy arguments
    broker.contracts = {}
    broker._get_instrument_token(symbol='SBIN-EQ', contracts=contracts_data) == '3045'
