import pytest
from unittest.mock import Mock, patch, call

from fastbt.brokers.master_trust import *
import requests
import json

contracts_data = {
    "NSE": [
        {
            "trading_symbol": "SBIN-EQ",
            "symbol": "SBIN",
            "exchange_code": 1,
            "exchange": "NSE",
            "company": "STATE BANK OF INDIA",
            "code": "3045",
        },
        {
            "trading_symbol": "SBT-EQ",
            "symbol": "SBT",
            "exchange_code": 1,
            "exchange": "NSE",
            "company": "STATE BANK OF TRAVANCORE",
            "code": "5316",
        },
    ],
    "NSE-OTH": [
        {
            "trading_symbol": "1018GS2026-GS",
            "symbol": "1018GS2026 GS",
            "exchange_code": 1,
            "exchange": "NSE",
            "company": "GOI LOAN 10.18% 2026",
            "code": "6833",
        }
    ],
}

sample_order_list = [
    {
        "symbol": "SBT-EQ",
        "product": "MIS",
        "status": "open",
        "quantity": 10,
        "price": 200,
        "oms_order_id": 10001,
    },
    {
        "symbol": "SBT-EQ",
        "product": "MIS",
        "status": "open",
        "quantity": 10,
        "price": 199,
        "oms_order_id": 10002,
    },
    {
        "symbol": "SBIN-EQ",
        "product": "MIS",
        "status": "open",
        "quantity": 10,
        "price": 400,
        "oms_order_id": 10003,
    },
    {
        "symbol": "SBIN-EQ",
        "product": "MIS",
        "status": "open",
        "quantity": 5,
        "price": 400,
        "oms_order_id": 10004,
    },
    {
        "symbol": "SBIN-EQ",
        "product": "BO",
        "status": "open",
        "quantity": 5,
        "price": 400,
        "oms_order_id": 10004,
    },
]


def order_args():
    normal = {
        "exchange": "NSE",
        "order_type": "LIMIT",
        "symbol": "SBIN-EQ",
        "price": 220,
        "side": "BUY",
        "validity": "DAY",
        "product": "MIS",
        "quantity": 1,
    }
    bracket = {
        "exchange": "NSE",
        "symbol": "SBT-EQ",
        "quantity": 1,
        "validity": "DAY",
        "square_off_value": 1301,
        "stop_loss_value": 1290,
        "price": 1299,
        "trigger_price": 1299,
        "trailing_stop_loss": 1,
        "order_type": "SL",
        "product": "BO",
        "side": "BUY",
        "is_trailing": False,
    }
    return dict(normal=normal, bracket=bracket)


@pytest.fixture
def mock_broker():
    broker = MasterTrust(
        client_id="XYZ", password="password", PIN=123456, secret="secret"
    )

    def pending_orders():
        # Adjustment to add bracket orders
        bracket_orders = [order_args()["bracket"]] * 4
        for i, bo in enumerate(bracket_orders):
            bo["status"] = "open"
            bo["symbol"] = bo["symbol"]
            bo["oms_order_id"] = 10007
            bo["instrument_token"] = 5316
            bo["quantity"] = i * 10
            bo["leg_order_indicator"] = "some_hex"
        return sample_order_list + bracket_orders

    broker.pending_orders = pending_orders

    # forcefully set some variables
    broker.contracts = {
        "NSE:SBIN-EQ": "3045",
        "NSE:SBT-EQ": "5316",
        "NSE:1018GS2026-GS": "6833",
        "NFO:SBIN-EQ": "3045",
        "NFO:SBT-EQ": "5316",
        "NFO:1018GS2026-GS": "6833",
    }
    broker._access_token = "abcd1234"
    broker._headers = {
        "Accept": "application/json",
        "Authorization": "Bearer abcd124",
        "Cache-Control": "no-cache",
    }
    return broker


@patch("requests.get")
def test_fetch_all_contracts(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    result = {"NSE:SBIN-EQ": "3045", "NSE:SBT-EQ": "5316", "NSE:1018GS2026-GS": "6833"}
    contracts = fetch_all_contracts(exchanges=["NSE"])
    assert result == contracts


@patch("requests.get")
def test_fetch_all_contracts_multiple_exchanges(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    result = {
        "NSE:SBIN-EQ": "3045",
        "NSE:SBT-EQ": "5316",
        "NSE:1018GS2026-GS": "6833",
        "NFO:SBIN-EQ": "3045",
        "NFO:SBT-EQ": "5316",
        "NFO:1018GS2026-GS": "6833",
    }
    contracts = fetch_all_contracts()
    assert result == contracts


@patch("requests.get")
def test_get_instrument_token(mock_get):
    mock_get.return_value.json.return_value = contracts_data
    contracts = fetch_all_contracts()
    token = get_instrument_token(contracts, "NSE", "SBIN-EQ")
    assert token == "3045"
    token = get_instrument_token(contracts, "NFO", "SBT-EQ")
    assert token == "5316"


def test_broker_get_instrument_token(mock_broker):
    broker = mock_broker
    print(broker.contracts)
    assert broker._get_instrument_token(symbol="SBIN-EQ") == "3045"


def test_broker_get_instrument_token_override_contracts():
    broker = MasterTrust("a", "b", "c", "d", "e")  # dummy arguments
    contracts = {
        "NSE:SBIN-EQ": "3045",
        "NSE:SBT-EQ": "5316",
        "NSE:1018GS2026-GS": "6833",
        "NFO:SBIN-EQ": "3045",
        "NFO:SBT-EQ": "5316",
        "NFO:1018GS2026-GS": "6833",
    }
    assert broker._get_instrument_token(symbol="SBIN-EQ", contracts=contracts) == "3045"


def test_broker_order_place(mock_broker):
    kwargs = order_args()["normal"]
    # To maintain order
    with patch("requests.post") as mock_post:
        broker = mock_broker
        broker.order_place(**kwargs)
        mock_post.assert_called()
        mock_post.assert_called_once()
        params = {
            "exchange": "NSE",
            "order_type": "LIMIT",
            "price": 220,
            "validity": "DAY",
            "product": "MIS",
            "quantity": 1,
            "instrument_token": "3045",
            "order_side": "BUY",
            "client_id": "XYZ",
            "user_order_id": 1000,
        }
        url = "https://masterswift-beta.mastertrust.co.in/api/v1/orders"
        mock_post.assert_called_with(url, headers=broker._headers, params=params)


def test_broker_order_place_other_args(mock_broker):
    kwargs = order_args()["normal"]
    kwargs.update({"trigger_price": 218, "order_type": "SLM"})
    with patch("requests.post") as mock_post:
        broker = mock_broker
        broker.order_place(**kwargs)
        mock_post.assert_called()
        mock_post.assert_called_once()
        params = {
            "exchange": "NSE",
            "order_type": "SLM",
            "price": 220,
            "validity": "DAY",
            "product": "MIS",
            "quantity": 1,
            "trigger_price": 218,
            "instrument_token": "3045",
            "order_side": "BUY",
            "client_id": "XYZ",
            "user_order_id": 1000,
        }
        url = "https://masterswift-beta.mastertrust.co.in/api/v1/orders"
        mock_post.assert_called_with(url, headers=broker._headers, params=params)


def test_broker_order_modify(mock_broker):
    kwargs = order_args()["normal"]
    kwargs.pop("side")
    kwargs.update({"oms_order_id": 11111})
    with patch("requests.put") as mock_put:
        broker = mock_broker
        broker.order_modify(**kwargs)
        mock_put.assert_called()
        mock_put.assert_called_once()
        params = {
            "exchange": "NSE",
            "order_type": "LIMIT",
            "price": 220,
            "validity": "DAY",
            "product": "MIS",
            "quantity": 1,
            "oms_order_id": 11111,
            "instrument_token": "3045",
            "client_id": "XYZ",
        }
        url = "https://masterswift-beta.mastertrust.co.in/api/v1/orders"
        mock_put.assert_called_with(url, headers=broker._headers, params=params)


def test_broker_place_bracket_order(mock_broker):
    kwargs = order_args()["bracket"]
    # To maintain order
    with patch("requests.post") as mock_post:
        broker = mock_broker
        broker.place_bracket_order(**kwargs)
        mock_post.assert_called()
        mock_post.assert_called_once()
        params = {
            "exchange": "NSE",
            "quantity": 1,
            "validity": "DAY",
            "square_off_value": 1301,
            "stop_loss_value": 1290,
            "price": 1299,
            "trigger_price": 1299,
            "trailing_stop_loss": 1,
            "order_type": "SL",
            "product": "BO",
            "is_trailing": False,
            "instrument_token": "5316",
            "order_side": "BUY",
            "client_id": "XYZ",
            "user_order_id": 1000,
        }
        url = "https://masterswift-beta.mastertrust.co.in/api/v1/orders/bracket"
        mock_post.assert_called_with(url, headers=broker._headers, params=params)


def test_broker_dict_filter(mock_broker):
    broker = mock_broker
    some_array = [{"a": i, "b": i**2} for i in range(10)]
    result = broker.filter(some_array, b=4)
    expected = [{"a": 2, "b": 4}]
    assert result == expected


def test_broker_modify_all_orders(mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        broker.modify_all_by_symbol(symbol="SBIN-EQ", price=400)
        assert mock_put.call_count == 3


def test_broker_set_headers():
    broker = MasterTrust("a", "b", "c", "d", "e")  # dummy arguments
    broker._access_token = "xyz123"
    headers = {
        "Accept": "application/json",
        "Authorization": "Bearer xyz123",
        "Cache-Control": "no-cache",
    }
    broker._set_headers()
    assert broker.headers == headers


def test_broker_set_headers_authenticate(mock_broker):
    with patch("fastbt.brokers.master_trust.MasterTrust._login") as login:
        with patch(
            "fastbt.brokers.master_trust.MasterTrust.get_access_token"
        ) as acc_token:
            acc_token.return_value = "xyz123"
            broker = mock_broker
            assert broker._access_token == "abcd1234"
            broker.authenticate(force=True)
            headers = {
                "Accept": "application/json",
                "Authorization": "Bearer xyz123",
                "Cache-Control": "no-cache",
            }
            assert broker._access_token == "xyz123"
            assert broker.headers == headers


@pytest.mark.parametrize("test_input,expected", [(2, 2), (3, 3), (None, 4), (10, 4)])
def test_broker_modify_bracket_target_n(test_input, expected, mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        broker.modify_bracket_target(symbol="SBT-EQ", target=110, n=test_input)
        assert mock_put.call_count == expected


def test_broker_modify_bracket_target_first(mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        broker.modify_bracket_target(symbol="SBT-EQ", target=110, first=True)
        assert mock_put.call_count == 1


@pytest.mark.parametrize("test_input,expected", [(2, 2), (3, 3), (None, 4), (10, 4)])
def test_broker_modify_bracket_stop_n(test_input, expected, mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        # This adjustment is done to change order status
        pending = []
        for order in broker.pending_orders():
            order["status"] = "trigger pending"
            pending.append(order)
        # Replace the pending orders function
        broker.pending_orders = lambda: pending
        broker.modify_bracket_stop(symbol="SBT-EQ", stop=90, n=test_input)
        assert mock_put.call_count == expected


@pytest.mark.parametrize("test_input,expected", [("MIS", 2), ("BO", 1)])
def test_modify_all_orders_filter(test_input, expected, mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        broker.modify_all_by_symbol(symbol="SBIN-EQ", product=test_input)
        assert mock_put.call_count == expected


@pytest.mark.parametrize("test_input,expected", [(25, 2), (0, 4), (5, 1), (60, 3)])
def test_exit_bracket_by_symbol_p(test_input, expected, mock_broker):
    with patch("requests.delete") as mock_put:
        broker = mock_broker
        broker.exit_bracket_by_symbol(symbol="SBT-EQ", p=test_input)
        assert mock_put.call_count == expected


@pytest.mark.parametrize("test_input,expected", [(25, 2), (0, 4), (5, 1), (60, 3)])
def test_broker_modify_bracket_stop_p(test_input, expected, mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        # This adjustment is done to change order status
        pending = []
        for order in broker.pending_orders():
            order["status"] = "trigger pending"
            pending.append(order)
        # Replace the pending orders function
        broker.pending_orders = lambda: pending
        broker.modify_bracket_stop(symbol="SBT-EQ", stop=90, p=test_input)
        assert mock_put.call_count == expected


@pytest.mark.parametrize("test_input,expected", [(25, 2), (0, 4), (5, 1), (60, 3)])
def test_broker_modify_bracket_target_p(test_input, expected, mock_broker):
    with patch("requests.put") as mock_put:
        broker = mock_broker
        # This adjustment is done to change order status
        pending = []
        for order in broker.pending_orders():
            order["status"] = "open"
            pending.append(order)
        # Replace the pending orders function
        broker.pending_orders = lambda: pending
        broker.modify_bracket_target(symbol="SBT-EQ", target=110, p=test_input)
        assert mock_put.call_count == expected
