import duckdb
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Union

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
    def get_instrument_data(self, date_str: str, strike: int, opt_type: str, start_time: str) -> Dict[str, Dict[str, float]]:
        """
        Returns the data for a specific option instrument from start_time till EOD.
        Output format: {'09:40:00': {'open': 130.5, 'high': 135.0, ...}, ...}
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
    Lazy fetcher for options backtesting using pure dicts and DuckDB.
    Avoids Pandas/Dataframes completely, using raw cursor tuples for performance.
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

    def get_instrument_data(self, date_str: str, strike: int, opt_type: str, start_time: str) -> Dict[str, Dict[str, float]]:
        """
        Fetches an instrument's data lazily from `start_time` till end of day.
        Returns native python nested dicts mapped by time.
        """
        query = f"""
            SELECT trade_time, open, high, low, close, volume
            FROM '{self.filepath}'
            WHERE trade_date = '{date_str}'
              AND option_type = '{opt_type}'
              AND strike = {strike}
              AND trade_time >= '{start_time}'
            ORDER BY trade_time
        """
        cursor = self.con.execute(query)
        results = cursor.fetchall()
        
        column_names = [desc[0] for desc in cursor.description]
        data = {}
        for row in results:
            time_str = str(row[0])
            # Construct inner dict dynamically mapping metric name to value
            data[time_str] = {column_names[i]: float(row[i]) for i in range(1, len(column_names))}
            
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
