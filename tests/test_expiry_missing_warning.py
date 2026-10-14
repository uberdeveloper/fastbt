"""Regression tests for missing expiry information (FastBT issue #29)."""

import logging
from unittest.mock import Mock

from fastbt.backtest.engine import group_by_expiry


def test_missing_expiries_warns_and_preserves_fallback(caplog):
    """An empty expiry list should be visible to the user, not silent."""
    source = Mock()
    source.get_expiries.return_value = []

    with caplog.at_level(logging.WARNING, logger="fastbt.backtest.engine"):
        groups = group_by_expiry(["2025-07-09"], source)

    assert groups == [["2025-07-09"]]
    assert "No valid expiry" in caplog.text
    assert "2025-07-09" in caplog.text


def test_each_missing_expiry_date_has_a_warning(caplog):
    """Multiple missing dates should produce one warning for each date."""
    source = Mock()
    source.get_expiries.return_value = []
    dates = ["2025-07-09", "2025-07-10"]

    with caplog.at_level(logging.WARNING, logger="fastbt.backtest.engine"):
        groups = group_by_expiry(dates, source)

    assert groups == [["2025-07-09"], ["2025-07-10"]]
    warning_messages = [
        item.getMessage()
        for item in caplog.records
        if item.name == "fastbt.backtest.engine"
        and item.levelno == logging.WARNING
    ]
    assert len(warning_messages) == 2
    assert "2025-07-09" in warning_messages[0]
    assert "2025-07-10" in warning_messages[1]
