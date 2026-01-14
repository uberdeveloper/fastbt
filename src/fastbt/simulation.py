"""
All simulations could be found here
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Union, Any, Callable
from scipy.stats import rv_continuous


def walk_forward(
    data: pd.DataFrame,
    period: str,
    parameters: List[str],
    column: str,
    function: Callable,
    num: int = 1,
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Perform a simple walk-forward test by selecting the best performing parameters
    in one period and applying them to the next.

    This function groups data by a specified period (e.g., Year, Month), calculates
    a performance metric for each parameter combination, and then shifts the "best"
    parameters forward by one period to see how they would have performed.

    Parameters
    ----------
    data : pd.DataFrame
        Input data with a DatetimeIndex.
    period : str
        Pandas frequency string (e.g., 'Y' for year, 'M' for month, 'Q' for quarter).
    parameters : List[str]
        List of column names representing different strategy parameters or factors.
    column : str
        The name of the column to evaluate performance on (e.g., 'returns').
    function : Callable
        A function to aggregate the performance column (e.g., np.sum, np.mean).
    num : int, optional
        The number of top/bottom performing parameter combinations to select, by default 1.
    ascending : bool, optional
        If True, selects the lowest values (bottom results). If False, selects the
        highest values (top results), by default False.

    Returns
    -------
    pd.DataFrame
        A merged DataFrame containing only the rows where the selected parameters
        from the previous period are present.

    Example
    -------
    >>> # Select the top performing parameter 'factor_a' for each year
    >>> # and see how it performs in the following year
    >>> results = walk_forward(df, period='Y', parameters=['factor_a'],
    ...                        column='returns', function='sum')
    """
    data["_period"] = data.index.to_period(period)
    columns = ["_period"] + parameters

    # Use string name for common aggregations to avoid FutureWarnings
    if function is sum or function is np.sum:
        function = "sum"
    elif function is np.mean:
        function = "mean"

    df = data.groupby(columns).agg({column: function}).reset_index()
    df2 = df.sort_values(by=column, ascending=ascending).groupby("_period").head(num)
    df2 = df2.set_index("_period").sort_index().shift(num)
    idx = df2.reset_index().drop(columns=column).dropna()
    return data.reset_index().merge(idx, on=columns)


def generate_correlated_data(
    correlations: List[float],
    n_samples: int = 100,
    reference_data: Optional[Union[List[float], np.ndarray, pd.Series]] = None,
    distribution: str = "normal",
    seed: Optional[int] = None,
    **dist_params: Any,
) -> pd.DataFrame:
    """
    **This code is AI generated with Claude 3.5 Sonnet using copilot**
    Generate correlated data with specified correlations to the first column.

    This function generates a dataset where subsequent columns have specified
    correlations with the first column (reference column). The data can be
    generated from various probability distributions or from a provided reference series.

    Args:
        correlations (List[float]): List of correlations with respect to the first column.
            Each value should be between -1 and 1.
            Example: [0.4, 0.3, -0.1] will generate 3 columns with these correlations
            to the reference column.

        n_samples (int, optional): Number of samples to generate. This parameter is ignored
            if reference_data is provided. Defaults to 100.

        reference_data (array-like, optional): Reference data series to use instead of
            random data. Can be a list, numpy array, or pandas Series. If provided,
            this will be used as the first column and other columns will be generated
            with specified correlations to this data. Defaults to None.

        distribution (str, optional): Name of the probability distribution to use.
            Supported distributions:
            - "normal": Optional params: loc (mean), scale (std)
            - "uniform": Optional params: low, high
            - "gamma": Optional params: shape, scale
            - "beta": Optional params: a, b
            - "exponential": Optional params: scale
            - "lognormal": Optional params: mean, sigma
            Defaults to "normal".

        seed (int, optional): Random seed for reproducibility. If None, uses current
            timestamp as seed. Defaults to None.

        **dist_params: Keyword arguments for distribution parameters.
            Examples:
            - For normal: loc=0, scale=1
            - For uniform: low=-1, high=1
            - For gamma: shape=2, scale=2
            - For beta: a=2, b=2
            - For exponential: scale=1
            - For lognormal: mean=0, sigma=1

    Returns:
        pd.DataFrame: A DataFrame containing the correlated data with columns:
            - 'reference': The reference column (either generated or provided)
            - 'var_1', 'var_2', etc.: Generated columns with specified correlations

    Raises:
        ValueError: If correlations are not between -1 and 1
        ValueError: If reference_data is not 1-dimensional
        ValueError: If distribution is not recognized
        ValueError: If distribution parameters are invalid

    Examples:
        >>> # Basic usage with normal distribution and auto seed
        >>> df = generate_correlated_data([0.4, 0.3, -0.1])

        >>> # Normal distribution with custom parameters
        >>> df = generate_correlated_data(
        ...     [0.4, 0.3, -0.1],
        ...     distribution="normal",
        ...     loc=5,
        ...     scale=2
        ... )

        >>> # Gamma distribution with custom parameters and specific seed
        >>> df = generate_correlated_data(
        ...     [0.4, 0.3, -0.1],
        ...     distribution="gamma",
        ...     seed=42,
        ...     shape=2,
        ...     scale=2
        ... )

        >>> # Using custom reference data with uniform distribution
        >>> ref_data = np.sin(np.linspace(0, 10, 100))
        >>> df = generate_correlated_data(
        ...     [0.4, 0.3, -0.1],
        ...     reference_data=ref_data,
        ...     distribution="uniform",
        ...     low=-2,
        ...     high=2
        ... )

    Notes:
        - The function uses the Cholesky decomposition method to generate
          correlated data
        - When reference_data is provided, it is standardized before generating
          correlations
        - The actual correlations might slightly differ from the target
          correlations due to random sampling
        - Distribution parameters are passed directly to numpy's random functions
        - When seed is None, the function uses the current timestamp as seed,
          ensuring different results on each run
        - When reference_data is provided, the output will maintain the original
          reference data values in the first column while ensuring the specified
          correlations are achieved with other columns.
    """
    # Validate inputs
    if not isinstance(correlations, (list, np.ndarray)):
        raise TypeError("correlations must be a list or numpy array")

    correlations = np.array(correlations, dtype=float)

    if not all(isinstance(c, (int, float)) for c in correlations):
        raise TypeError("All correlations must be numbers")
    if not all(-1 <= c <= 1 for c in correlations):
        raise ValueError("All correlations must be between -1 and 1")

    if n_samples < 10:
        raise ValueError("n_samples must be at least 10 for reliable correlations")

    if len(correlations) >= n_samples:
        raise ValueError("Number of correlations must be less than n_samples")

    # Set random seed
    if seed is None:
        np.random.seed(int(pd.Timestamp.now().timestamp()))
    else:
        np.random.seed(seed)

    # Number of variables
    n_vars = len(correlations) + 1

    # Dictionary of supported distributions and their sampling functions
    distribution_functions = {
        "normal": lambda size: np.random.normal(
            loc=dist_params.get("loc", 0), scale=dist_params.get("scale", 1), size=size
        ),
        "uniform": lambda size: np.random.uniform(
            low=dist_params.get("low", -1), high=dist_params.get("high", 1), size=size
        ),
        "gamma": lambda size: np.random.gamma(
            shape=dist_params.get("shape", 2),
            scale=dist_params.get("scale", 2),
            size=size,
        ),
        "beta": lambda size: np.random.beta(
            a=dist_params.get("a", 2), b=dist_params.get("b", 2), size=size
        ),
        "exponential": lambda size: np.random.exponential(
            scale=dist_params.get("scale", 1), size=size
        ),
        "lognormal": lambda size: np.random.lognormal(
            mean=dist_params.get("mean", 0),
            sigma=dist_params.get("sigma", 1),
            size=size,
        ),
    }

    if distribution not in distribution_functions:
        raise ValueError(
            f"Unsupported distribution: {distribution}. "
            f"Supported distributions: {list(distribution_functions.keys())}"
        )

    random_generator = distribution_functions[distribution]

    # Handle reference data
    original_reference = None
    if reference_data is not None:
        if not isinstance(reference_data, (list, np.ndarray, pd.Series)):
            raise TypeError(
                "reference_data must be a list, numpy array, or pandas Series"
            )
        reference_data = np.array(reference_data, dtype=float)
        if len(reference_data.shape) != 1:
            raise ValueError("reference_data must be 1-dimensional")
        n_samples = len(reference_data)
        # Store original reference data
        original_reference = reference_data.copy()
        # Standardize the reference data for correlation calculations
        reference_series = (reference_data - np.mean(reference_data)) / np.std(
            reference_data
        )

    # Create the correlation matrix
    corr_matrix = np.ones((n_vars, n_vars))
    for i in range(1, n_vars):
        corr_matrix[0, i] = correlations[i - 1]
        corr_matrix[i, 0] = correlations[i - 1]

    # Fill the rest of the correlation matrix
    for i in range(1, n_vars):
        for j in range(1, n_vars):
            if i != j:
                corr_matrix[i, j] = 0.01

    # Ensure the matrix is positive definite
    min_eig = np.min(np.linalg.eigvals(corr_matrix))
    if min_eig < 0:
        corr_matrix += (-min_eig + 0.01) * np.eye(n_vars)

    # Generate the correlated data
    if reference_data is None:
        # Generate initial random data
        uncorrelated = random_generator((n_samples, n_vars))
        # Standardize the generated data
        uncorrelated = (uncorrelated - np.mean(uncorrelated, axis=0)) / np.std(
            uncorrelated, axis=0
        )

        # Apply correlations using Cholesky decomposition
        L = np.linalg.cholesky(corr_matrix)
        correlated = uncorrelated @ L.T
    else:
        # Use the provided reference data for the first column
        correlated = np.zeros((n_samples, n_vars))
        correlated[:, 0] = reference_series

        # Generate remaining columns with specified correlations
        remaining_cols = random_generator((n_samples, n_vars - 1))
        # Standardize the generated data
        remaining_cols = (remaining_cols - np.mean(remaining_cols, axis=0)) / np.std(
            remaining_cols, axis=0
        )

        # Calculate the coefficients needed for the correlations
        for i in range(n_vars - 1):
            target_correlation = correlations[i]
            remaining_cols[:, i] = (
                target_correlation * reference_series
                + np.sqrt(1 - target_correlation**2) * remaining_cols[:, i]
            )

        correlated[:, 1:] = remaining_cols

    # Create DataFrame
    columns = ["reference"] + [f"var_{i+1}" for i in range(len(correlations))]
    df = pd.DataFrame(correlated, columns=columns)

    # If original reference data exists, replace the standardized version
    if original_reference is not None:
        df["reference"] = original_reference

    return df


def _draw_samples(
    n: int,
    distribution: Optional[Union[rv_continuous, Callable, np.ndarray, pd.Series]],
    default_loc: float,
    default_scale: float,
    **kwargs,
) -> np.ndarray:
    """
    Draw n samples from a given scipy distribution, callable, or empirical array.
    Fallback to normal with specified loc/scale.
    """
    if distribution is None:
        return np.random.normal(loc=default_loc, scale=default_scale, size=n)
    elif hasattr(distribution, "rvs"):
        return distribution.rvs(size=n)
    elif callable(distribution):
        try:
            return distribution(size=n, **kwargs)
        except TypeError:
            return distribution(n)
    elif isinstance(distribution, (np.ndarray, pd.Series, list)):
        arr = np.asarray(distribution)
        return np.random.choice(arr, size=n, replace=True)
    else:
        raise ValueError(
            "Distribution must be None, a scipy.stats distribution, a callable, or an array/Series."
        )


def generate_synthetic_stock_data(
    start_date: str = "2010-01-01",
    end_date: str = "2020-12-31",
    initial_price: float = 100.0,
    scenario: str = "neutral",
    trading_days: int = 252,
    seed: Optional[int] = None,
    mu_bull: float = 0.15,
    mu_bear: float = -0.15,
    mu_neutral: float = 0.02,
    sigma_bull: float = 0.20,
    sigma_bear: float = 0.25,
    sigma_neutral: float = 0.18,
    jump_prob: float = 0.002,
    jump_scale: float = 2.0,
    distribution: Optional[
        Union[rv_continuous, Callable, np.ndarray, pd.Series]
    ] = None,
    jump_distribution: Optional[
        Union[rv_continuous, Callable, np.ndarray, pd.Series]
    ] = None,
) -> pd.DataFrame:
    """
    Generate synthetic daily stock OHLCV data using geometric Brownian motion,
    or custom/empirical return distributions.

    Parameters
    ----------
    start_date : str
        Start date in 'YYYY-MM-DD' format.
    end_date : str
        End date in 'YYYY-MM-DD' format.
    initial_price : float
        Starting price for the simulation.
    scenario : str
        Market scenario: "bullish", "bearish", or "neutral".
    trading_days : int
        Number of trading days per year (default: 252).
    seed : int, optional
        Random seed for reproducibility.
    mu_bull, mu_bear, mu_neutral : float
        Annualized drift for each scenario.
    sigma_bull, sigma_bear, sigma_neutral : float
        Annualized volatility for each scenario.
    jump_prob : float
        Probability of a jump event on any day.
    jump_scale : float
        Multiplicative scale for jump size (used if jump_distribution is not given).
    distribution : scipy.stats frozen distribution, callable, array-like, or None
        Distribution to sample returns from. If None, uses normal distribution.
    jump_distribution : same as above, optional
        Distribution to sample jump sizes from. If None, uses normal.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: ['Date', 'Open', 'High', 'Low', 'Close', 'Volume'].

    Examples
    --------
    >>> # Generate bullish stock data
    >>> df = generate_synthetic_stock_data(
    ...     start_date="2025-01-01",
    ...     end_date="2025-12-31",
    ...     scenario="bullish",
    ...     mu_bull=0.15,
    ...     sigma_bull=0.20,
    ...     seed=42
    ... )
    >>> # Generate with heavy-tailed returns
    >>> from scipy.stats import t
    >>> t_dist = t(df=3, loc=0, scale=0.018)
    >>> df = generate_synthetic_stock_data(
    ...     start_date="2025-01-01",
    ...     end_date="2025-03-01",
    ...     distribution=t_dist,
    ...     seed=202
    ... )
    """
    if seed is not None:
        np.random.seed(seed)

    # Scenario params
    if scenario == "bullish":
        mu, sigma = mu_bull, sigma_bull
    elif scenario == "bearish":
        mu, sigma = mu_bear, sigma_bear
    else:
        mu, sigma = mu_neutral, sigma_neutral

    dates = pd.bdate_range(start=start_date, end=end_date)
    n = len(dates)
    dt = 1 / trading_days

    # Generate returns
    loc = (mu - 0.5 * sigma**2) * dt
    scale = sigma * np.sqrt(dt)
    returns = _draw_samples(n, distribution, loc, scale, mu=mu, sigma=sigma, dt=dt)

    # Add jumps
    jumps_mask = np.random.binomial(1, jump_prob, n)
    if jump_distribution is not None:
        jumps = _draw_samples(
            n, jump_distribution, 0, sigma * jump_scale, mu=mu, sigma=sigma, dt=dt
        )
    else:
        jumps = np.random.normal(0, sigma * jump_scale, n)
    returns = returns + jumps_mask * jumps

    # Geometric Brownian motion path
    price = np.empty(n)
    price[0] = initial_price
    for t in range(1, n):
        price[t] = price[t - 1] * np.exp(returns[t])

    # OHLCV simulation
    df = pd.DataFrame(index=dates)
    df["Close"] = price
    df["Open"] = df["Close"].shift(1).fillna(initial_price)
    high_noise = np.abs(np.random.normal(0, sigma * 0.18, n))
    low_noise = np.abs(np.random.normal(0, sigma * 0.18, n))
    df["High"] = df[["Open", "Close"]].max(axis=1) * (1 + high_noise)
    df["Low"] = df[["Open", "Close"]].min(axis=1) * (1 - low_noise)

    base_vol = np.random.randint(8e4, 2e6)
    vol_noise = np.random.normal(0, base_vol * 0.025, n)
    if scenario == "bullish":
        vol_trend = np.linspace(1, 1.2, n)
    elif scenario == "bearish":
        vol_trend = np.linspace(1, 0.8, n)
    else:
        vol_trend = np.ones(n)
    volume = np.abs(np.cumsum(vol_noise) + base_vol) * vol_trend
    df["Volume"] = (volume * (1 + np.random.normal(0, 0.1, n))).astype(int)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.index.name = "Date"
    return df.reset_index()


def generate_synthetic_intraday_data(
    start_date: str = "2010-01-01",
    end_date: str = "2010-01-01",
    initial_price: float = 100.0,
    scenario: str = "neutral",
    freq: str = "5min",
    start_hour: Union[int, float] = 9.5,
    end_hour: Union[int, float] = 16,
    continuous: bool = False,
    seed: Optional[int] = None,
    distribution: Optional[
        Union[rv_continuous, Callable, np.ndarray, pd.Series]
    ] = None,
    jump_distribution: Optional[
        Union[rv_continuous, Callable, np.ndarray, pd.Series]
    ] = None,
    mu_bull: float = 0.15,
    mu_bear: float = -0.15,
    mu_neutral: float = 0.02,
    sigma_bull: float = 0.20,
    sigma_bear: float = 0.25,
    sigma_neutral: float = 0.18,
    jump_prob: float = 0.002,
    jump_scale: float = 2.0,
) -> pd.DataFrame:
    """
    Generate synthetic intraday OHLCV data for a specified date/frequency/session.

    Parameters
    ----------
    start_date, end_date : str
        Start and end date in 'YYYY-MM-DD' format.
    initial_price : float
        Starting price.
    scenario : str
        Market scenario: "bullish", "bearish", or "neutral".
    freq : str
        Bar frequency (e.g., "1min", "5min"). Pandas offset alias.
    start_hour, end_hour : int or float
        Session hours (e.g., 9.5 for 9:30am). Ignored if continuous.
    continuous : bool
        If True, generate continuous 24h data (crypto). Otherwise, session-based.
    seed : int, optional
        Random seed.
    distribution : scipy.stats frozen distribution, callable, array-like, or None
        Distribution for returns.
    jump_distribution : same as above, optional
        Distribution for jump sizes.
    mu_bull, mu_bear, mu_neutral : float
        Annualized drift for each scenario.
    sigma_bull, sigma_bear, sigma_neutral : float
        Annualized volatility for each scenario.
    jump_prob : float
        Probability of a jump per bar.
    jump_scale : float
        Scale for jump magnitude.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns: ['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume'].

    Notes
    -----
    - **Volatility Scaling**: Annual volatility is scaled based on the number of bars per year.
    - **Overnight Jumps**: If `continuous=False`, a random jump is added between one day's
      close and the next day's open.
    - **Session Open**: A specific volatility boost is applied to the first bar of the session.

    Examples
    --------
    >>> # Generate 5-minute NYSE session data
    >>> df = generate_synthetic_intraday_data(
    ...     start_date="2025-01-01",
    ...     end_date="2025-01-05",
    ...     freq="5min",
    ...     start_hour=9.5,
    ...     end_hour=16.0
    ... )
    >>> # Generate 1-hour continuous crypto data
    >>> df_crypto = generate_synthetic_intraday_data(
    ...     start_date="2025-01-01",
    ...     end_date="2025-01-07",
    ...     freq="1H",
    ...     continuous=True
    ... )
    """
    if seed is not None:
        np.random.seed(seed)

    # Scenario params
    if scenario == "bullish":
        mu, sigma = mu_bull, sigma_bull
    elif scenario == "bearish":
        mu, sigma = mu_bear, sigma_bear
    else:
        mu, sigma = mu_neutral, sigma_neutral

    if continuous:
        date_range = pd.date_range(start=start_date, end=end_date)
    else:
        date_range = pd.bdate_range(start=start_date, end=end_date)

    # Handle deprecated frequency aliases
    if freq == "H":
        freq = "h"

    freq_td = pd.to_timedelta(pd.tseries.frequencies.to_offset(freq))
    freq_minutes = freq_td.seconds // 60

    # dt for each bar
    minutes_per_year = 252 * (6.5 * 60) if not continuous else 365.25 * 24 * 60
    dt = freq_minutes / minutes_per_year

    all_rows = []
    last_close = initial_price

    for day in date_range:
        if continuous:
            start_dt = pd.Timestamp(day.date())
            end_dt = start_dt + pd.Timedelta(days=1)
            times = pd.date_range(
                start=start_dt, end=end_dt, freq=freq, inclusive="left"
            )
        else:
            start_dt = pd.Timestamp(day.date()) + pd.Timedelta(hours=float(start_hour))
            end_dt = pd.Timestamp(day.date()) + pd.Timedelta(hours=float(end_hour))
            times = pd.date_range(
                start=start_dt, end=end_dt, freq=freq, inclusive="left"
            )
            if len(times) == 0:
                continue

        n = len(times)
        loc = (mu - 0.5 * sigma**2) * dt
        scale = sigma * np.sqrt(dt)
        returns = _draw_samples(n, distribution, loc, scale, mu=mu, sigma=sigma, dt=dt)

        # Add jumps during session randomly
        jumps_mask = np.random.binomial(1, jump_prob, n)
        if jump_distribution is not None:
            jumps = _draw_samples(
                n, jump_distribution, 0, sigma * jump_scale, mu=mu, sigma=sigma, dt=dt
            )
        else:
            jumps = np.random.normal(0, sigma * jump_scale, n)
        returns = returns + jumps_mask * jumps

        # Insert a larger jump at session open if not continuous
        if not continuous:
            session_jump = np.random.normal(0, sigma * jump_scale * 0.7)
            returns[0] += session_jump

        # Price path
        price = np.empty(n)
        price[0] = last_close * np.exp(returns[0])
        for t in range(1, n):
            price[t] = price[t - 1] * np.exp(returns[t])

        ohlc = pd.DataFrame(index=times)
        ohlc["Close"] = price
        ohlc["Open"] = ohlc["Close"].shift(1)
        ohlc.iloc[0, ohlc.columns.get_loc("Open")] = last_close
        high_noise = np.abs(np.random.normal(0, sigma * 0.06, n))
        low_noise = np.abs(np.random.normal(0, sigma * 0.06, n))
        ohlc["High"] = ohlc[["Open", "Close"]].max(axis=1) * (1 + high_noise)
        ohlc["Low"] = ohlc[["Open", "Close"]].min(axis=1) * (1 - low_noise)
        base_vol = np.random.randint(100, 10000)
        vol_noise = np.random.normal(0, base_vol * 0.08, n)
        if scenario == "bullish":
            vol_trend = np.linspace(1, 1.1, n)
        elif scenario == "bearish":
            vol_trend = np.linspace(1, 0.9, n)
        else:
            vol_trend = np.ones(n)
        volume = np.abs(np.cumsum(vol_noise) + base_vol) * vol_trend
        ohlc["Volume"] = (volume * (1 + np.random.normal(0, 0.1, n))).astype(int)
        ohlc.index.name = "DateTime"
        all_rows.append(ohlc)
        last_close = float(price[-1])

        # If not continuous, add an overnight jump for next day's session open
        if not continuous and day != date_range[-1]:
            overnight_jump = np.random.normal(0, sigma * jump_scale * 1.2)
            last_close = last_close * np.exp(overnight_jump)

    df_intraday = pd.concat(all_rows).reset_index()
    return df_intraday


def _time_path_generator(
    initial_price: float,
    drift: float = 0.0,
    vol: float = 0.2,
    tick_size: float = 0.05,
    intensity: float = 1.0,
    fat_tails: bool = False,
    degrees_of_freedom: int = 3,
    use_quotes: bool = False,
    spread: float = 0.01,
    seed: Optional[int] = None,
    seconds_per_year: int = 31536000,
    vol_multiplier: float = 1.0,
):
    """
    Internal time-based market generator using GBM and Poisson arrivals.
    """
    from scipy.stats import t

    rng = np.random.RandomState(seed)
    price = initial_price
    current_time = (
        pd.Timestamp("2025-01-01") if seed is not None else pd.Timestamp.now()
    )

    params = {
        "drift": drift,
        "vol": vol,
        "tick_size": tick_size,
        "intensity": intensity,
        "fat_tails": fat_tails,
        "degrees_of_freedom": degrees_of_freedom,
        "spread": spread,
        "seconds_per_year": seconds_per_year,
        "vol_multiplier": vol_multiplier,
    }

    while True:
        # Time Advancement (Poisson Arrival)
        dt_seconds = rng.exponential(1.0 / params["intensity"])
        current_time += pd.Timedelta(seconds=dt_seconds)
        dt_years = dt_seconds / params["seconds_per_year"]

        effective_vol = params["vol"] * params["vol_multiplier"]

        # Price Move (GBM + optional Fat Tails)
        if params["fat_tails"]:
            shock = t.rvs(df=params["degrees_of_freedom"], random_state=rng)
        else:
            shock = rng.standard_normal()

        returns = (params["drift"] - 0.5 * effective_vol**2) * dt_years + (
            effective_vol * np.sqrt(dt_years) * shock
        )
        price *= np.exp(returns)

        # Snap to tick size for the output only
        snapped_price = round(price / params["tick_size"]) * params["tick_size"]

        if use_quotes:
            half_spread = (snapped_price * params["spread"]) / 2
            data = {
                "timestamp": current_time,
                "bid": round((snapped_price - half_spread) / params["tick_size"])
                * params["tick_size"],
                "ask": round((snapped_price + half_spread) / params["tick_size"])
                * params["tick_size"],
                "mid_price": snapped_price,
                "raw_price": price,
            }
        else:
            data = {
                "timestamp": current_time,
                "price": snapped_price,
                "size": rng.randint(1, 100),
                "raw_price": price,
            }

        update = yield data
        if update and isinstance(update, dict):
            params.update(update)


def _sequence_path_generator(
    initial_price: float,
    distribution: Optional[Any] = None,
    tick_size: float = 0.05,
    use_quotes: bool = False,
    spread: float = 0.01,
    seed: Optional[int] = None,
    start_time: Optional[pd.Timestamp] = None,
    time_multiplier: float = 1.0,
):
    """
    Internal sequence-based market generator using IID steps.
    """
    rng = np.random.RandomState(seed)
    price = initial_price
    init_real_time = pd.Timestamp.now()
    if start_time is None:
        start_time = init_real_time

    if distribution is None:
        from scipy.stats import lognorm
        distribution = lognorm(s=0.01)

    params = {
        "tick_size": tick_size,
        "spread": spread,
        "time_multiplier": time_multiplier,
    }

    while True:
        # Time Logic: Label based on real wall clock elapsed
        wall_elapsed = pd.Timestamp.now() - init_real_time
        current_time = start_time + wall_elapsed * params["time_multiplier"]

        # Price Move: Single IID sample
        # Returns raw price back
        if hasattr(distribution, "rvs"):
            sample = distribution.rvs(random_state=rng)
        elif callable(distribution):
            sample = distribution(random_state=rng)
        else:
            sample = 1.0

        # Application: price multiplication
        price *= sample

        snapped_price = round(price / params["tick_size"]) * params["tick_size"]

        if use_quotes:
            half_spread = (snapped_price * params["spread"]) / 2
            data = {
                "timestamp": current_time,
                "bid": round((snapped_price - half_spread) / params["tick_size"])
                * params["tick_size"],
                "ask": round((snapped_price + half_spread) / params["tick_size"])
                * params["tick_size"],
                "mid_price": snapped_price,
                "raw_price": price,
            }
        else:
            data = {
                "timestamp": current_time,
                "price": snapped_price,
                "size": rng.randint(1, 100),
                "raw_price": price,
            }

        update = yield data
        if update and isinstance(update, dict):
            params.update(update)
            if "distribution" in update:
                distribution = update["distribution"]


def tick_generator(
    initial_price: float,
    mode: str = "time",
    **kwargs,
):
    """
    An infinite generator that yields individual trade ticks one at a time.

    Parameters
    ----------
    initial_price : float
        The starting price.
    mode : str, optional
        'time' for continuous GBM using intensity, 'sequence' for IID steps.
    **kwargs :
        For 'time' mode: drift, vol, tick_size, intensity, fat_tails,
        degrees_of_freedom, seconds_per_year, vol_multiplier, seed.
        For 'sequence' mode: distribution, tick_size, start_time, time_multiplier, seed.

    Yields
    -------
    dict
        A dictionary containing: timestamp, price, size, and raw_price.
    """
    if mode == "time":
        return _time_path_generator(initial_price=initial_price, **kwargs)
    else:
        return _sequence_path_generator(initial_price=initial_price, **kwargs)


def quote_generator(
    initial_price: float,
    mode: str = "time",
    **kwargs,
):
    """
    An infinite generator that yields Bid/Ask quotes.

    Parameters
    ----------
    initial_price : float
        The starting price.
    mode : str, optional
        'time' or 'sequence'.
    **kwargs :
        Same as tick_generator, plus 'spread'.

    Yields
    -------
    dict
        A dictionary containing: timestamp, bid, ask, mid_price, and raw_price.
    """
    if mode == "time":
        return _time_path_generator(
            initial_price=initial_price, use_quotes=True, **kwargs
        )
    else:
        return _sequence_path_generator(
            initial_price=initial_price, use_quotes=True, **kwargs
        )
