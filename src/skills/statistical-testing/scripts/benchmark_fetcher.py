"""
Benchmark Fetcher Module

Fetches benchmark data from yfinance with graceful error handling.
"""

import pandas as pd
import numpy as np
from typing import Optional, Tuple, Dict
from datetime import datetime, timedelta
import warnings


def fetch_benchmark(
    ticker: str,
    start_date: str,
    end_date: str,
    interval: str = '1d'
) -> Optional[pd.DataFrame]:
    """
    Fetch benchmark data from yfinance
    
    Args:
        ticker: Ticker symbol (e.g., '^GSPC', 'NIFTY50.NS', 'BTC-USD')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval ('1d', '1wk', '1mo')
        
    Returns:
        DataFrame with date and returns columns, or None if fetch fails
    """
    try:
        import yfinance as yf
    except ImportError:
        print("⚠️ yfinance not installed. Install with: pip install yfinance")
        return None
    
    try:
        # Fetch data
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=True
        )
        
        if df.empty:
            print(f"⚠️ No data returned for {ticker}")
            return None
        
        # Calculate returns
        df['returns'] = df['Close'].pct_change()
        
        # Clean up
        df = df[['returns']].dropna()
        df.index.name = 'date'
        df = df.reset_index()
        
        return df
        
    except Exception as e:
        print(f"⚠️ Failed to fetch {ticker}: {e}")
        return None


def match_benchmark_to_strategy(
    strategy_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    date_column: str = 'date',
    strategy_returns_column: str = 'returns',
    benchmark_returns_column: str = 'returns'
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Align benchmark returns to strategy dates
    
    Args:
        strategy_df: Strategy DataFrame with date and returns
        benchmark_df: Benchmark DataFrame with date and returns
        date_column: Name of date column
        strategy_returns_column: Name of strategy returns column
        benchmark_returns_column: Name of benchmark returns column
        
    Returns:
        Tuple of (strategy_returns, benchmark_returns) aligned arrays
    """
    # Ensure date columns are datetime
    strategy_df = strategy_df.copy()
    benchmark_df = benchmark_df.copy()
    
    strategy_df[date_column] = pd.to_datetime(strategy_df[date_column])
    benchmark_df[date_column] = pd.to_datetime(benchmark_df[date_column])
    
    # Merge on date
    merged = pd.merge(
        strategy_df[[date_column, strategy_returns_column]],
        benchmark_df[[date_column, benchmark_returns_column]],
        on=date_column,
        how='inner',
        suffixes=('_strategy', '_benchmark')
    )
    
    if len(merged) == 0:
        raise ValueError("No overlapping dates between strategy and benchmark")
    
    # Check coverage
    coverage = len(merged) / len(strategy_df) * 100
    if coverage < 80:
        warnings.warn(
            f"Only {coverage:.1f}% of strategy dates have benchmark data. "
            f"Results may not be reliable."
        )
    
    strategy_returns = merged[strategy_returns_column].values
    benchmark_returns = merged[benchmark_returns_column].values
    
    return strategy_returns, benchmark_returns


class BenchmarkSelector:
    """
    Helper class for benchmark selection
    
    Note: This provides common ticker mappings, but LLM should infer
    from context when possible.
    """
    
    # Common benchmark tickers (for reference, not exhaustive)
    COMMON_BENCHMARKS = {
        # US Equity
        'spy': 'SPY',
        's&p500': '^GSPC',
        'sp500': '^GSPC',
        'nasdaq': '^IXIC',
        'dow': '^DJI',
        
        # India Equity
        'nifty50': '^NSEI',
        'nifty': '^NSEI',
        'sensex': '^BSESN',
        
        # International
        'ftse': '^FTSE',
        'dax': '^GDAXI',
        'nikkei': '^N225',
        
        # Crypto
        'bitcoin': 'BTC-USD',
        'btc': 'BTC-USD',
        'ethereum': 'ETH-USD',
        'eth': 'ETH-USD',
        
        # Commodities
        'gold': 'GC=F',
        'silver': 'SI=F',
        'crude': 'CL=F',
        'oil': 'CL=F',
        
        # Bonds
        'us10y': '^TNX',
        'us2y': '^IRX',
    }
    
    @staticmethod
    def suggest_ticker(benchmark_name: str) -> Optional[str]:
        """
        Suggest ticker symbol from common name
        
        Args:
            benchmark_name: Common name (e.g., 'nifty50', 'spy')
            
        Returns:
            Ticker symbol or None if not found
        """
        name_lower = benchmark_name.lower().strip()
        return BenchmarkSelector.COMMON_BENCHMARKS.get(name_lower)
    
    @staticmethod
    def format_ticker_for_yfinance(ticker: str, country: Optional[str] = None) -> str:
        """
        Format ticker for yfinance
        
        Args:
            ticker: Base ticker symbol
            country: Country code for international tickers
            
        Returns:
            Formatted ticker
        """
        # Handle special cases
        if country and country.lower() == 'india':
            if not ticker.endswith('.NS') and not ticker.endswith('.BO'):
                # Try NSE first
                return f"{ticker}.NS"
        
        return ticker


def get_frequency_from_data(df: pd.DataFrame, date_column: str = 'date') -> str:
    """
    Infer data frequency from timestamps
    
    Args:
        df: DataFrame with date column
        date_column: Name of date column
        
    Returns:
        Frequency string ('1d', '1wk', '1mo')
    """
    dates = pd.to_datetime(df[date_column])
    diffs = dates.diff().dropna()
    
    median_diff = diffs.median()
    
    if median_diff <= pd.Timedelta(days=1):
        return '1d'
    elif median_diff <= pd.Timedelta(days=7):
        return '1wk'
    else:
        return '1mo'


# Example usage
if __name__ == "__main__":
    # Example 1: Fetch SPY data
    print("Fetching SPY benchmark...")
    spy_data = fetch_benchmark(
        ticker='SPY',
        start_date='2020-01-01',
        end_date='2025-12-31',
        interval='1d'
    )
    
    if spy_data is not None:
        print(f"✓ Fetched {len(spy_data)} observations")
        print(spy_data.head())
    print()
    
    # Example 2: Suggest ticker
    selector = BenchmarkSelector()
    suggested = selector.suggest_ticker('nifty50')
    print(f"Suggested ticker for 'nifty50': {suggested}")
    print()
    
    # Example 3: Match benchmark to strategy
    # Create sample strategy data
    strategy_df = pd.DataFrame({
        'date': pd.date_range('2020-01-01', periods=100),
        'returns': np.random.normal(0.001, 0.02, 100)
    })
    
    if spy_data is not None:
        # Trim benchmark to match strategy dates
        benchmark_subset = spy_data[
            (spy_data['date'] >= strategy_df['date'].min()) &
            (spy_data['date'] <= strategy_df['date'].max())
        ]
        
        try:
            strat_ret, bench_ret = match_benchmark_to_strategy(
                strategy_df,
                benchmark_subset
            )
            print(f"Aligned {len(strat_ret)} observations")
            print(f"Strategy mean: {np.mean(strat_ret):.6f}")
            print(f"Benchmark mean: {np.mean(bench_ret):.6f}")
        except Exception as e:
            print(f"Alignment failed: {e}")
