import logging

import duckdb
from abc import ABC, abstractmethod
from typing import Dict, List, Union

logger = logging.getLogger(__name__)


class DataSource(ABC):
    """
    Abstract base class for lazy data sources.
    Uses pure Python dictionaries for high performance matching.
    """

    @abstractmethod
    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        """
        Returns a time-sequenced dictionary of the underlying asset's master clock.
        Output format: {'09:15:00': 23620.55, '09:16:00': 23618.10, ...}
        """
        pass

    @abstractmethod
    def get_instrument_data(
        self, date_str: str, strike: int, opt_type: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Returns the FULL-DAY data for a specific option instrument.
        No start_time filter — always fetches from first to last bar.
        Output format: {'09:15:00': {'open': 130.5, 'high': 135.0, ...}, ...}
        """
        pass

    @abstractmethod
    def get_available_dates(self) -> List[str]:
        """Returns all valid trade dates in the dataset."""
        pass

    @abstractmethod
    def get_expiries(self, trade_date: str) -> List[str]:
        """Returns all option expiries trading on the specified date."""
        pass


class DuckDBParquetLoader(DataSource):
    """
    Production DataSource for options backtesting using DuckDB + Parquet.

    Uses raw cursor tuples (no pandas) for maximum speed.
    All instrument fetches are full-day (09:15 to 15:30) — no start_time filter.
    The cache in BarContext is the guard against look-ahead bias, not the query.
    """

    def __init__(self, filepath: str):
        self.filepath = filepath
        # Read-only memory connection for extreme speed
        self.con = duckdb.connect()

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        """
        Fetches underlying price for the entire day.
        Returns a dictionary: {'09:15:00': 22000.50, ...}
        """
        query = f"""
            SELECT DISTINCT trade_time, underlying_price
            FROM '{self.filepath}'
            WHERE trade_date = '{date_str}'
              AND underlying_price IS NOT NULL
            ORDER BY trade_time
        """
        cursor = self.con.execute(query)
        # Directly construct dict from tuples, bypassing any DataFrame logic
        # row[0] is time (usually datetime.time), row[1] is price
        return {str(row[0]): float(row[1]) for row in cursor.fetchall()}

    def get_instrument_data(
        self, date_str: str, strike: int, opt_type: str
    ) -> Dict[str, Dict[str, float]]:
        """
        Fetches FULL-DAY OHLCV data for one option instrument.

        No time filter — returns all bars from 09:15 to 15:30.
        Look-ahead bias prevention is handled by BarContext (clock-gated access),
        not by restricting the query.

        Returns:
            Nested dict: {'09:15:00': {'open': x, 'high': x, 'low': x,
                                       'close': x, 'volume': x}, ...}
        """
        query = f"""
            SELECT trade_time, open, high, low, close, volume
            FROM '{self.filepath}'
            WHERE trade_date = '{date_str}'
              AND option_type = '{opt_type}'
              AND strike = {strike}
            ORDER BY trade_time
        """
        cursor = self.con.execute(query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]

        data: Dict[str, Dict[str, float]] = {}
        for row in results:
            time_str = str(row[0])
            data[time_str] = {
                column_names[i]: float(row[i]) for i in range(1, len(column_names))
            }
        return data

    def _get_query(self, query: str) -> duckdb.DuckDBPyConnection:
        """Executes the given SQL query and returns the DuckDB cursor."""
        return self.con.execute(query)

    def get_available_dates(self) -> List[str]:
        """Returns a sorted list of all unique trade dates in the file."""
        query = f"SELECT DISTINCT trade_date FROM '{self.filepath}' ORDER BY trade_date"
        cursor = self.con.execute(query)
        return [str(row[0]) for row in cursor.fetchall()]

    def get_available_expiries(self) -> List[str]:
        """Returns a sorted list of all unique expiry dates in the file."""
        query = f"SELECT DISTINCT expiry FROM '{self.filepath}' ORDER BY expiry"
        cursor = self.con.execute(query)
        return [str(row[0]) for row in cursor.fetchall()]

    def get_expiries(self, trade_date: str) -> List[str]:
        """Returns all valid option expiry dates trading on a given trade date."""
        query = f"SELECT DISTINCT expiry FROM '{self.filepath}' WHERE trade_date = '{trade_date}' ORDER BY expiry"
        cursor = self.con.execute(query)
        return [str(row[0]) for row in cursor.fetchall()]

    @staticmethod
    def get_atm_strike(spot_price: float, step: int = 50) -> int:
        """Helper to calculate closest ATM strike."""
        return int(round(spot_price / step) * step)

    @staticmethod
    def get_strike(spot: float, step: int, distance: float) -> Union[int, float]:
        """Calculate strike price based on spot, step and distance from ATM."""
        atm = int(round(spot / step) * step)
        return atm + (distance * step)
