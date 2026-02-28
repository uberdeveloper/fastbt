import duckdb
import pandas as pd
from typing import Dict, Any

class ParquetDataLoader:
    """
    Lazy fetcher for options backtesting using pure dicts and DuckDB.
    Optimized for intraday 1-minute OHLC data.
    """
    def __init__(self, filepath: str):
        self.filepath = filepath
        self.con = duckdb.connect()

    def get_underlying_data(self, date_str: str) -> Dict[str, float]:
        """
        Fetches the underlying price for the entire day.
        Returns a dictionary mapped by time: {'09:15:00': 22000.50, ...}
        This acts as the master loop clock.
        """
        query = f"""
            SELECT trade_time, underlying_price 
            FROM '{self.filepath}'
            WHERE trade_date = '{date_str}'
            GROUP BY trade_time, underlying_price
            ORDER BY trade_time
        """
        df = self.con.execute(query).df()
        
        # Convert to pure dict mapping time string to float spot price
        if df.empty:
            return {}
            
        # Ensure we just grab the first valid price per minute if duplicates exist
        df = df.drop_duplicates(subset=['trade_time'])
        return dict(zip(df['trade_time'].astype(str), df['underlying_price']))

    def get_instrument_data(self, date_str: str, strike: int, opt_type: str, start_time: str) -> Dict[str, Dict[str, float]]:
        """
        Fetches an instrument's data lazily from `start_time` till end of day.
        Returns native python dicts keyed by time for O(1) loop lookup.
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
        df = self.con.execute(query).df()
        
        if df.empty:
            return {}
            
        # Convert to dict of dicts: {'09:16:00': {'open': 100, 'close': 102}, ...}
        df.set_index('trade_time', inplace=True)
        # Use 'index' orient to get nested dicts mapping time -> metrics
        raw_dict = df.to_dict(orient='index')
        
        # Ensure outer keys are standardized strings
        return {str(k): v for k, v in raw_dict.items()}
