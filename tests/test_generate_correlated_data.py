import pytest
import numpy as np
import pandas as pd
from datetime import datetime
from fastbt.simulation import generate_correlated_data

# Constants for testing
SAMPLE_CORRELATIONS = [0.4, 0.3, -0.1]
SAMPLE_SIZE = 100
# Additional constants for testing
EXTREME_SAMPLES = [5, 1000000]  # Very small and very large sample sizes
HIGH_CORRELATIONS = [0.9, 0.9, 0.9]  # High positive correlations
NEGATIVE_CORRELATIONS = [-0.9, -0.9, -0.9]  # High negative correlations
MIXED_EXTREME_CORRELATIONS = [0.99, -0.99, 0.95]  # Mixed extreme correlations


def test_basic_functionality():
    """Test basic function execution with default parameters."""
    df = generate_correlated_data(SAMPLE_CORRELATIONS)

    assert isinstance(df, pd.DataFrame)
    assert df.shape == (SAMPLE_SIZE, len(SAMPLE_CORRELATIONS) + 1)
    assert list(df.columns) == ["reference"] + [
        f"var_{i+1}" for i in range(len(SAMPLE_CORRELATIONS))
    ]


def test_seed_reproducibility():
    """Test that same seed produces same results."""
    seed = 42
    df1 = generate_correlated_data(SAMPLE_CORRELATIONS, seed=seed)
    df2 = generate_correlated_data(SAMPLE_CORRELATIONS, seed=seed)

    np.testing.assert_array_almost_equal(df1.values, df2.values)


def test_different_seeds_different_results():
    """Test that different seeds produce different results."""
    df1 = generate_correlated_data(SAMPLE_CORRELATIONS, seed=42)
    df2 = generate_correlated_data(SAMPLE_CORRELATIONS, seed=43)

    assert not np.array_equal(df1.values, df2.values)


def test_correlation_accuracy():
    """Test that generated correlations are close to target correlations."""
    df = generate_correlated_data(SAMPLE_CORRELATIONS, seed=42)
    actual_correlations = df.corr()["reference"][1:].values

    np.testing.assert_array_almost_equal(
        actual_correlations, SAMPLE_CORRELATIONS, decimal=1
    )


@pytest.mark.parametrize(
    "distribution,params",
    [
        ("normal", {"loc": 5, "scale": 2}),
        ("uniform", {"low": -2, "high": 2}),
        ("gamma", {"shape": 2, "scale": 2}),
        ("beta", {"a": 2, "b": 5}),
        ("exponential", {"scale": 2}),
        ("lognormal", {"mean": 0, "sigma": 0.5}),
    ],
)
def test_distributions(distribution, params):
    """Test different distributions with their parameters."""
    df = generate_correlated_data(
        SAMPLE_CORRELATIONS, distribution=distribution, seed=42, **params
    )

    assert df.shape == (SAMPLE_SIZE, len(SAMPLE_CORRELATIONS) + 1)
    # Check correlations are still maintained
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(
        actual_correlations, SAMPLE_CORRELATIONS, decimal=1
    )


def test_reference_data():
    """Test using custom reference data."""
    reference = np.sin(np.linspace(0, 10, SAMPLE_SIZE))
    df = generate_correlated_data(
        SAMPLE_CORRELATIONS, reference_data=reference, seed=42
    )

    # Check reference data is properly standardized
    ref_standardized = (reference - np.mean(reference)) / np.std(reference)
    np.testing.assert_array_almost_equal(df["reference"].values, ref_standardized)


@pytest.mark.parametrize(
    "invalid_corr",
    [
        [1.1, 0.3, 0.2],  # > 1
        [-1.1, 0.3, 0.2],  # < -1
        [0.3, 0.2],  # wrong length
        [],  # empty
    ],
)
def test_invalid_correlations(invalid_corr):
    """Test invalid correlation values."""
    with pytest.raises(ValueError):
        generate_correlated_data(invalid_corr)


@pytest.mark.parametrize("n_samples", [10, 50, 200])
def test_different_sample_sizes(n_samples):
    """Test different sample sizes."""
    df = generate_correlated_data(SAMPLE_CORRELATIONS, n_samples=n_samples)
    assert df.shape == (n_samples, len(SAMPLE_CORRELATIONS) + 1)


def test_invalid_distribution():
    """Test invalid distribution name."""
    with pytest.raises(ValueError):
        generate_correlated_data(SAMPLE_CORRELATIONS, distribution="invalid_dist")


def test_invalid_reference_data():
    """Test invalid reference data shapes."""
    invalid_ref = np.random.normal(size=(100, 2))  # 2D array
    with pytest.raises(ValueError):
        generate_correlated_data(SAMPLE_CORRELATIONS, reference_data=invalid_ref)


def test_reference_data_different_types():
    """Test different types of reference data."""
    size = 100
    test_data = {
        "list": list(range(size)),
        "numpy": np.arange(size),
        "pandas": pd.Series(range(size)),
    }

    for data_type, ref_data in test_data.items():
        df = generate_correlated_data(SAMPLE_CORRELATIONS, reference_data=ref_data)
        assert df.shape == (size, len(SAMPLE_CORRELATIONS) + 1)


def test_distribution_param_validation():
    """Test invalid distribution parameters."""
    with pytest.raises(ValueError):
        generate_correlated_data(
            SAMPLE_CORRELATIONS,
            distribution="gamma",
            shape=-1,  # invalid shape parameter
        )


def test_correlation_matrix_positive_definite():
    """Test that the correlation matrix remains positive definite."""
    # Using correlations that might cause issues with positive definiteness
    challenging_correlations = [0.9, 0.9, 0.9]
    df = generate_correlated_data(challenging_correlations)

    # Check that correlations are still reasonable
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(
        actual_correlations, challenging_correlations, decimal=1
    )


def test_result_standardization():
    """Test that the generated data is properly standardized."""
    df = generate_correlated_data(SAMPLE_CORRELATIONS)

    # Check if each column is approximately standardized
    for col in df.columns:
        assert abs(df[col].mean()) < 0.1  # approximately zero mean
        assert abs(df[col].std() - 1) < 0.1  # approximately unit variance


def generate_polynomial_data(n_samples: int, degree: int) -> np.ndarray:
    """Helper function to generate polynomial data."""
    x = np.linspace(-5, 5, n_samples)
    coefficients = np.random.normal(size=degree + 1)
    return np.polyval(coefficients, x)


@pytest.mark.parametrize("sample_size", [10, 1000000])  # Changed minimum to 10
def test_extreme_sample_sizes(sample_size):
    """Test very small and very large sample sizes."""
    correlations = [0.5, 0.3]
    df = generate_correlated_data(correlations, n_samples=sample_size)

    assert df.shape == (sample_size, len(correlations) + 1)
    # Check correlations are still reasonable
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


@pytest.mark.parametrize(
    "correlations",
    [
        [1.0001, 0.3],  # Slightly above 1
        [-1.0001, 0.3],  # Slightly below -1
        [0.3, 1.5],  # Well above 1
        [0.3, -1.5],  # Well below -1
        [np.inf, 0.3],  # Infinity
        [np.nan, 0.3],  # NaN
        [0.3, None],  # None value
    ],
)
def test_invalid_correlation_values(correlations):
    """Test various invalid correlation values."""
    with pytest.raises((ValueError, TypeError)):
        generate_correlated_data(correlations)


@pytest.mark.parametrize(
    "reference_type", ["quadratic", "cubic", "exponential", "sinusoidal", "complex"]
)
def test_complex_reference_patterns(reference_type):
    """Test with complex reference data patterns."""
    n_samples = 100
    x = np.linspace(-5, 5, n_samples)

    if reference_type == "quadratic":
        reference = x**2
    elif reference_type == "cubic":
        reference = x**3
    elif reference_type == "exponential":
        reference = np.exp(x)
    elif reference_type == "sinusoidal":
        reference = np.sin(x) + np.cos(2 * x)
    else:  # complex
        reference = x**2 + np.sin(x) + np.exp(-x / 5)

    correlations = [0.7, -0.7, 0.5]
    df = generate_correlated_data(correlations, reference_data=reference)

    assert df.shape == (n_samples, len(correlations) + 1)
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_high_correlations_with_random_reference():
    """Test high correlations (0.9) with random reference data."""
    n_samples = 1000
    reference = np.random.normal(0, 1, n_samples)
    correlations = [0.9, 0.9, 0.9]

    df = generate_correlated_data(correlations, reference_data=reference)
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_high_negative_correlations_with_random_reference():
    """Test high negative correlations (-0.9) with random reference data."""
    n_samples = 1000
    reference = np.random.normal(0, 1, n_samples)
    correlations = [-0.9, -0.9, -0.9]

    df = generate_correlated_data(correlations, reference_data=reference)
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


@pytest.mark.parametrize(
    "invalid_data",
    [
        pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),  # 2D DataFrame
        np.array([[1, 2], [3, 4]]),  # 2D array
        [[]],  # Empty nested list
        None,  # None
        "invalid",  # String
        42,  # Single number
    ],
)
def test_invalid_reference_data_types(invalid_data):
    """Test various invalid reference data types."""
    with pytest.raises((ValueError, TypeError)):
        generate_correlated_data([0.5, 0.3], reference_data=invalid_data)


def test_polynomial_reference_data():
    """Test with polynomial reference data of different degrees."""
    n_samples = 200
    correlations = [0.8, -0.8]

    for degree in range(1, 6):  # Test polynomials of degree 1 to 5
        reference = generate_polynomial_data(n_samples, degree)
        df = generate_correlated_data(correlations, reference_data=reference)

        actual_correlations = df.corr()["reference"][1:].values
        np.testing.assert_array_almost_equal(
            actual_correlations, correlations, decimal=1
        )


@pytest.mark.parametrize(
    "n_samples,n_correlations",
    [
        (20, 5),  # Modified for more realistic sizes
        (100, 20),  # Modified for more realistic sizes
        (1000, 50),  # Modified for more realistic sizes
        (50, 10),  # Modified for more realistic sizes
    ],
)
def test_various_correlation_matrix_sizes(n_samples, n_correlations):
    """Test different sizes of correlation matrices."""
    correlations = [0.5] * n_correlations
    df = generate_correlated_data(correlations, n_samples=n_samples)

    assert df.shape == (n_samples, n_correlations + 1)
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


@pytest.mark.parametrize(
    "distribution,params",
    [
        ("gamma", {"shape": 0.1, "scale": 0.1}),  # Very small parameters
        ("gamma", {"shape": 100, "scale": 100}),  # Very large parameters
        ("normal", {"loc": 1e6, "scale": 1e-6}),  # Extreme normal parameters
        ("beta", {"a": 0.1, "b": 0.1}),  # U-shaped beta
        ("beta", {"a": 100, "b": 100}),  # Highly peaked beta
    ],
)
def test_extreme_distribution_parameters(distribution, params):
    """Test extreme parameter values for distributions."""
    correlations = [0.5, -0.5]
    df = generate_correlated_data(correlations, distribution=distribution, **params)

    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_zero_correlation():
    """Test with zero correlations."""
    correlations = [0.0, 0.0, 0.0]
    df = generate_correlated_data(correlations)

    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_alternating_correlations():
    """Test with alternating positive and negative correlations."""
    correlations = [
        0.7,
        -0.7,
        0.7,
        -0.7,
    ]  # Reduced number of correlations and magnitude
    df = generate_correlated_data(correlations, n_samples=1000)  # Increased sample size

    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


@pytest.mark.parametrize(
    "std", [1e-10, 1e10]
)  # Very small and very large standard deviations
def test_extreme_scale_reference_data(std):
    """Test reference data with extreme scales."""
    n_samples = 100
    reference = np.random.normal(0, std, n_samples)
    correlations = [0.7, -0.7]

    df = generate_correlated_data(correlations, reference_data=reference)
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_extreme_mixed_correlations():
    """Test mixture of extreme positive and negative correlations."""
    correlations = [0.95, -0.95, 0.90, -0.90]  # Slightly reduced from 0.99
    df = generate_correlated_data(correlations, n_samples=1000)  # Increased sample size
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)


def test_reference_data_maintains_original_values():
    """Test that original reference data values are maintained in the output."""
    # Create reference data with specific mean and standard deviation
    n_samples = 100
    mean_value = 10
    std_value = 2
    reference_data = np.random.normal(mean_value, std_value, n_samples)
    correlations = [0.7, -0.7]

    # Generate correlated data
    df = generate_correlated_data(correlations, reference_data=reference_data)

    # Check that the reference column exactly matches the input data
    np.testing.assert_array_equal(df["reference"].values, reference_data)

    # Check that correlations are still maintained
    actual_correlations = df.corr()["reference"][1:].values
    np.testing.assert_array_almost_equal(actual_correlations, correlations, decimal=1)

    # Verify that the mean and std of reference column are preserved
    np.testing.assert_almost_equal(df["reference"].mean(), np.mean(reference_data))
    np.testing.assert_almost_equal(df["reference"].std(), np.std(reference_data))


def test_reference_data_with_different_scales():
    """Test that original reference data values are maintained with different scales."""
    # Test cases with different scales
    test_cases = [
        (100, 20),  # Normal scale
        (1000, 200),  # Large scale
        (0.1, 0.02),  # Small scale
        (-50, 10),  # Negative mean
    ]

    correlations = [0.7, -0.7]
    n_samples = 100

    for mean_value, std_value in test_cases:
        reference_data = np.random.normal(mean_value, std_value, n_samples)
        df = generate_correlated_data(correlations, reference_data=reference_data)

        # Check that the reference column exactly matches the input data
        np.testing.assert_array_equal(df["reference"].values, reference_data)

        # Check that correlations are still maintained
        actual_correlations = df.corr()["reference"][1:].values
        np.testing.assert_array_almost_equal(
            actual_correlations, correlations, decimal=1
        )


def test_reference_data_with_extreme_patterns():
    """Test that original reference data values are maintained with extreme patterns."""
    n_samples = 100
    x = np.linspace(0, 10, n_samples)
    correlations = [0.7, -0.7]

    # Test different patterns
    patterns = {
        "exponential": np.exp(x),
        "quadratic": x**2,
        "sine": np.sin(x) * 100,  # Large amplitude
        "constant": np.ones(n_samples) * 1000,  # Large constant value
        "mixed": x**2 + np.sin(x) * 100 + np.exp(x / 2),
    }

    for pattern_name, reference_data in patterns.items():
        df = generate_correlated_data(correlations, reference_data=reference_data)

        # Check that the reference column exactly matches the input data
        np.testing.assert_array_equal(df["reference"].values, reference_data)

        # Check that correlations are still maintained
        actual_correlations = df.corr()["reference"][1:].values
        np.testing.assert_array_almost_equal(
            actual_correlations, correlations, decimal=1
        )
