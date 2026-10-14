"""Regression tests for past and valid expiries (FastBT issue #29)."""

import logging
from unittest.mock import Mock

from fastbt.backtest.engine import group_by_expiry


def test_only_expired_contracts_logs_warning(caplog):
    """Expiries earlier than the trade date are not valid choices."""
    source = Mock()
    source.get_expiries.return_value = ["2025-07-01", "2025-07-08"]

    with caplog.at_level(logging.WARNING, logger="fastbt.backtest.engine"):
        groups = group_by_expiry(["2025-07-09"], source)

    assert groups == [["2025-07-09"]]
    assert "No valid expiry" in caplog.text
    assert "2025-07-09" in caplog.text


def test_valid_expiries_group_normally_without_warning(caplog):
    """A normal expiry group must not trigger a false warning."""
    source = Mock()
    source.get_expiries.return_value = ["2025-07-17", "2025-07-10"]

    with caplog.at_level(logging.WARNING, logger="fastbt.backtest.engine"):
        groups = group_by_expiry(["2025-07-08", "2025-07-09"], source)

    assert groups == [["2025-07-08", "2025-07-09"]]
    assert "No valid expiry" not in caplog.text
    assert source.get_expiries.call_count == 2
