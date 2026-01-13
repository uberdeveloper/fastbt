import pytest
import numpy as np
import pandas as pd
from scipy.stats import norm, t, lognorm, laplace
from fastbt.simulation import *
from pandas.testing import assert_frame_equal

test_data = (
    pd.read_csv("tests/data/index.csv", parse_dates=["date"])
    .set_index("date")
    .sort_index()
)


def test_walk_forward_simple():
    expected = pd.read_csv("tests/data/is_pret.csv", parse_dates=["date"])
    result = walk_forward(test_data, "Y", ["is_pret"], "ret", "sum")
    del result["_period"]
    assert len(result) == len(expected)
    assert_frame_equal(expected, result)


def test_daily_random_walk():
    """Test generation of a basic random walk (log-return normal, lognormal price path)."""
    df = generate_synthetic_stock_data(
        start_date="2023-01-01", end_date="2023-01-31", scenario="neutral", seed=42
    )
    assert "Close" in df.columns
    assert (df["Close"] > 0).all()


def test_daily_lognormal_distribution():
    """Test generation using lognormal distribution for returns."""
    lognorm_dist = lognorm(s=0.05, scale=np.exp(0.0))
    df = generate_synthetic_stock_data(
        start_date="2023-01-01",
        end_date="2023-01-10",
        distribution=lognorm_dist,
        seed=123,
    )
    assert isinstance(df, pd.DataFrame)
    assert (df["Close"] > 0).all()
    assert df["Close"].max() > 1.5 * df["Close"].iloc[0]


def test_daily_extreme_values():
    """Test generation with extreme jumps and fatter tail distribution."""
    laplace_dist = laplace(loc=0, scale=0.05)
    df = generate_synthetic_stock_data(
        start_date="2023-01-01",
        end_date="2023-01-20",
        distribution=laplace_dist,
        jump_prob=0.2,
        jump_scale=8.0,
        seed=321,
    )
    assert (df["Close"] > 0).all()
    returns = np.log(df["Close"]).diff().dropna()
    assert (np.abs(returns) > 0.10).any()


def test_daily_scipy_distribution():
    """Test Student-t distributed returns."""
    dist = t(df=5, loc=0, scale=0.01)
    df = generate_synthetic_stock_data(
        distribution=dist, seed=0, start_date="2023-01-01", end_date="2023-01-10"
    )
    assert isinstance(df, pd.DataFrame)
    assert (df["Close"] > 0).all()


def test_daily_empirical_distribution():
    """Test empirical bootstrapping from synthetic returns."""
    empirical = np.random.normal(0, 0.01, 500)
    df = generate_synthetic_stock_data(
        distribution=empirical, seed=1, start_date="2023-01-01", end_date="2023-01-10"
    )
    assert isinstance(df, pd.DataFrame)
    assert (df["Close"] > 0).all()


def test_daily_custom_callable_distribution():
    """Test custom callable distribution for returns."""

    def sampler(size, **kwargs):
        return np.full(size, 0.001)

    df = generate_synthetic_stock_data(
        distribution=sampler, seed=2, start_date="2023-01-01", end_date="2023-01-10"
    )
    assert isinstance(df, pd.DataFrame)
    assert (df["Close"] > 0).all()


def test_intraday_exchange_session():
    """Test intraday data for exchange session (not continuous)."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-02",
        end_date="2023-01-02",
        freq="5min",
        start_hour=9.5,
        end_hour=16,
        continuous=False,
        seed=42,
    )
    assert "DateTime" in df.columns
    assert (df["Open"] > 0).all()
    assert (df["Close"] > 0).all()


def test_intraday_continuous():
    """Test continuous (24h) intraday data generation."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-02",
        end_date="2023-01-02",
        freq="15min",
        continuous=True,
        seed=42,
    )
    assert "DateTime" in df.columns
    assert (df["Open"] > 0).all()
    assert (df["Close"] > 0).all()


def test_intraday_empirical():
    """Test intraday data with empirical return distribution."""
    returns = np.random.normal(0, 0.001, 1000)
    df = generate_synthetic_intraday_data(
        start_date="2023-01-09",
        end_date="2023-01-09",
        freq="5min",
        continuous=True,
        distribution=returns,
        seed=42,
    )
    assert (df["Close"] > 0).all()


def test_intraday_custom_callable():
    """Test intraday data with custom callable distribution."""

    def call(size, **kwargs):
        return np.full(size, 0.0005)

    df = generate_synthetic_intraday_data(
        start_date="2023-01-03",
        end_date="2023-01-03",
        freq="5min",
        continuous=True,
        distribution=call,
        seed=42,
    )
    assert (df["Close"] > 0).all()


def test_edge_case_one_day_intraday():
    """Test edge case of single day, hourly bars, continuous market."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-01",
        end_date="2023-01-01",
        freq="1h",
        continuous=True,
        seed=42,
    )
    assert df.shape[0] >= 24


def test_jump_distribution():
    """Test custom jump distribution for large, positive jumps."""
    jump_dist = norm(loc=0.01, scale=0.01)
    df = generate_synthetic_stock_data(
        start_date="2023-01-01",
        end_date="2023-01-10",
        jump_prob=1.0,
        jump_distribution=jump_dist,
        seed=42,
    )
    assert (df["Close"] > 0).all()
    assert df["Close"].iloc[-1] > df["Close"].iloc[0]


def test_bullish_high_volatility():
    """Test bullish scenario with high volatility."""
    # Using a longer range to allow drift to become more apparent
    df = generate_synthetic_stock_data(
        start_date="2023-01-01",
        end_date="2023-03-31",
        scenario="bullish",
        mu_bull=0.5,
        sigma_bull=0.01,
        seed=42,
    )
    assert (df["Close"] > 0).all()
    assert df["Close"].iloc[-1] > df["Close"].iloc[0]  # Upward drift


def test_bearish_frequent_large_jumps():
    """Test bearish scenario with frequent large negative jumps."""
    from scipy.stats import norm

    df = generate_synthetic_stock_data(
        start_date="2023-01-01",
        # Use 15 days to allow enough samples for jumps
        end_date="2023-01-15",
        scenario="bearish",
        mu_bear=-0.3,
        sigma_bear=0.45,
        jump_prob=0.4,
        jump_distribution=norm(loc=-0.15, scale=0.04),
        seed=77,
    )
    assert (df["Close"] > 0).all()
    assert df["Close"].iloc[-1] < df["Close"].iloc[0]  # Downward drift


def test_intraday_high_intraday_volatility():
    """Test intraday with high volatility."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-02",
        end_date="2023-01-02",
        freq="1min",
        start_hour=9.5,
        end_hour=16,
        continuous=False,
        sigma_bull=0.6,
        scenario="bullish",
        seed=88,
    )
    assert (df["Close"] > 0).all()
    # Should show measurable variance in returns
    returns = np.log(df["Close"]).diff().dropna()
    assert returns.std() > 0.001


def test_intraday_crypto_scenario():
    """Test continuous crypto-style intraday scenario with neutral volatility."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-03",
        end_date="2023-01-03",
        freq="15min",
        continuous=True,
        scenario="neutral",
        sigma_neutral=0.25,
        seed=99,
    )
    assert (df["Close"] > 0).all()
    assert df.shape[0] > 80  # Should be many bars for a day


def test_intraday_stress_heavy_tailed():
    """Stress test: heavy-tailed returns and frequent jumps in intraday."""
    df = generate_synthetic_intraday_data(
        start_date="2023-01-04",
        end_date="2023-01-04",
        freq="10min",
        continuous=True,
        distribution=laplace(loc=0, scale=0.03),
        jump_prob=0.15,
        jump_scale=5.0,
        seed=111,
    )
    returns = np.log(df["Close"]).diff().dropna()
    assert (df["Close"] > 0).all()
    assert (np.abs(returns) > 0.05).any()  # At least one big move


def test_tick_generator_basic():
    """Test basic functionality of tick generator."""
    gen = tick_generator(initial_price=100.0, tick_size=0.01)
    tick = next(gen)
    assert "price" in tick
    assert "timestamp" in tick
    assert tick["price"] == 100.0


def test_tick_generator_send():
    """Test updating parameters via .send()."""
    gen = tick_generator(initial_price=100.0)
    next(gen)
    # Update volatility and drift
    gen.send({"vol": 0.5, "drift": 0.1})
    # The next tick should exist and work
    tick = next(gen)
    assert isinstance(tick["price"], float)


def test_quote_generator_basic():
    """Test basic functionality of quote generator."""
    gen = quote_generator(initial_price=100.0, spread=0.01)
    quote = next(gen)
    assert "bid" in quote
    assert "ask" in quote
    assert quote["ask"] > quote["bid"]
    # 1% spread on 100 should be 1.0, so bid/ask should be 99.5/100.5
    assert quote["bid"] == 99.5
    assert quote["ask"] == 100.5


def test_tick_generator_price_movement():
    """
    Regression test: Ensure price actually moves and doesn't get stuck
    at initial_price due to rounding small moves.
    """
    # Use a small vol and small tick size - previously this would stay at 100.0
    gen = tick_generator(initial_price=100.0, vol=0.5, tick_size=0.01, seed=42)
    prices = [next(gen)["price"] for _ in range(200)]
    unique_prices = set(prices)
    # With 200 ticks and 50% vol, the price SHOULD definitely move
    assert len(unique_prices) > 1, f"Price stayed stuck at {unique_prices}"
