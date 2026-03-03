"""
fastbt.backtest.data
====================
Data sources for the FastBT backtesting engine.

All concrete loaders implement the DataSource ABC so strategies are
completely agnostic to the underlying file format:

    # Swap one line — zero strategy changes needed
    loader = DuckDBParquetLoader("/data/q1_2025.parquet")
    loader = DuckDBVortexLoader("/data/q1_2025.vortex")   # identical API
"""

import logging

import duckdb
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union

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

    def __init__(self, filepath: str, extra_columns: Optional[List[str]] = None):
        """
        Args:
            filepath:      Path to the Parquet file.
            extra_columns: Additional columns to fetch alongside OHLCV.
                           Example: ["delta", "calc_iv", "open_interest"]
                           Defaults to OHLCV only.
        """
        self.filepath = filepath
        self.extra_columns: List[str] = extra_columns or []
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
        base_cols = "trade_time, open, high, low, close, volume"
        if self.extra_columns:
            extra = ", ".join(self.extra_columns)
            select_cols = f"{base_cols}, {extra}"
        else:
            select_cols = base_cols

        query = f"""
            SELECT {select_cols}
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


class DuckDBVortexLoader(DataSource):
    """
    Drop-in replacement for DuckDBParquetLoader that reads .vortex files.

    Uses DuckDB's vortex extension (requires DuckDB >= 1.4.2) via
    ``read_vortex('path')`` instead of a bare parquet path literal.
    Everything else — method signatures, return types, query logic —
    is identical to DuckDBParquetLoader.

    Usage:
        loader = DuckDBVortexLoader("/data/q1_2025.vortex")
        # then pass to BacktestEngine exactly as you would a parquet loader

    Convert parquet → vortex once:
        con = duckdb.connect()
        con.execute("INSTALL vortex; LOAD vortex;")
        con.execute(
            "COPY (SELECT * FROM 'data.parquet') TO 'data.vortex' (FORMAT vortex)"
        )
    """

    def __init__(self, filepath: str, extra_columns: Optional[List[str]] = None):
        """
        Args:
            filepath:      Path to the .vortex file.
            extra_columns: Additional columns to fetch alongside OHLCV.
                           Example: ["delta", "calc_iv", "open_interest"]
                           Defaults to OHLCV only.
        """
        self.filepath = filepath
        self.extra_columns: List[str] = extra_columns or []
        self.con = duckdb.connect()
        # Install once; subsequent calls are no-ops if already installed
        self.con.execute("INSTALL vortex; LOAD vortex;")

    # ── Internal helper ────────────────────────────────────────────────────────

    def _src(self) -> str:
        """Return the read_vortex(...) table expression used in all queries."""
        return f"read_vortex('{self.filepath}')"

    # ── DataSource interface ───────────────────────────────────────────────────

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        """
        Fetches underlying price for the entire day.
        Returns a dictionary: {'09:15:00': 22000.50, ...}
        """
        query = f"""
            SELECT DISTINCT trade_time, underlying_price
            FROM {self._src()}
            WHERE trade_date = '{date_str}'
              AND underlying_price IS NOT NULL
            ORDER BY trade_time
        """
        cursor = self.con.execute(query)
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
        base_cols = "trade_time, open, high, low, close, volume"
        if self.extra_columns:
            extra = ", ".join(self.extra_columns)
            select_cols = f"{base_cols}, {extra}"
        else:
            select_cols = base_cols

        query = f"""
            SELECT {select_cols}
            FROM {self._src()}
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

    def get_available_dates(self) -> List[str]:
        """Returns a sorted list of all unique trade dates in the file."""
        query = f"SELECT DISTINCT trade_date FROM {self._src()} ORDER BY trade_date"
        cursor = self.con.execute(query)
        return [str(row[0]) for row in cursor.fetchall()]

    def get_available_expiries(self) -> List[str]:
        """Returns a sorted list of all unique expiry dates in the file."""
        query = f"SELECT DISTINCT expiry FROM {self._src()} ORDER BY expiry"
        cursor = self.con.execute(query)
        return [str(row[0]) for row in cursor.fetchall()]

    def get_expiries(self, trade_date: str) -> List[str]:
        """Returns all valid option expiry dates trading on a given trade date."""
        query = f"""
            SELECT DISTINCT expiry FROM {self._src()}
            WHERE trade_date = '{trade_date}' ORDER BY expiry
        """
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
