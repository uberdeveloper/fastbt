"""
All simulations could be found here
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Union, Any, Callable


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
    Do a simple walk forward test based on constant train
    and test period on a pandas dataframe
    data
        data as a pandas dataframe
    period
        period as a pandas frequency string
    factors
        list of parameters to be used in the test.
        These must be columns in the dataframe
    column
        The column to be used for running the test
    function
        The function to be run on the column
    num
        The number of results to be used for walk forward
    ascending
        Whether the top or bottom results to be taken
    """
    data["_period"] = data.index.to_period(period)
    columns = ["_period"] + parameters
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
    """
    # Validate inputs
    if not isinstance(correlations, (list, np.ndarray)):
        raise TypeError("correlations must be a list or numpy array")

    # Convert correlations to numpy array for easier handling
    correlations = np.array(correlations, dtype=float)

    # Validate correlation values
    if not all(isinstance(c, (int, float)) for c in correlations):
        raise TypeError("All correlations must be numbers")
    if not all(-1 <= c <= 1 for c in correlations):
        raise ValueError("All correlations must be between -1 and 1")

    # Validate sample size
    if n_samples < 10:  # Minimum sample size for reliable correlations
        raise ValueError("n_samples must be at least 10 for reliable correlations")

    # Validate number of correlations
    if len(correlations) >= n_samples:
        raise ValueError("Number of correlations must be less than n_samples")

    # Validate reference_data
    if reference_data is not None:
        if not isinstance(reference_data, (list, np.ndarray, pd.Series)):
            raise TypeError(
                "reference_data must be a list, numpy array, or pandas Series"
            )
        reference_data = np.array(reference_data, dtype=float)
        if len(reference_data.shape) != 1:
            raise ValueError("reference_data must be 1-dimensional")

    # Set random seed
    if seed is None:
        np.random.seed(int(pd.Timestamp.now().timestamp()))
    else:
        np.random.seed(seed)

    # Number of variables (correlations + 1 for the reference column)
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

    # Handle reference data if provided
    if reference_data is not None:
        reference_series = np.array(reference_data)
        if len(reference_series.shape) > 1:
            raise ValueError("reference_data must be a 1-dimensional array")
        n_samples = len(reference_series)
        # Standardize the reference data
        reference_series = (reference_series - np.mean(reference_series)) / np.std(
            reference_series
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

    return df
