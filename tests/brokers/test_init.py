import warnings

warnings.simplefilter("always")


def test_warning_broker():
    with warnings.catch_warnings(record=True) as w:
        from fastbt.brokers.zerodha import Zerodha

        message = str(w[-1].message)
        assert len(w) == 1
        assert issubclass(w[-1].category, DeprecationWarning)
        assert "Brokers support would be removed from version 0.7.0" in message
        assert "omspy" in message
