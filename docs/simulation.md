# Simulation and Synthetic Data

The `fastbt.simulation` module provides tools for generating synthetic market data and performing walk-forward analysis. This is essential for testing strategy robustness when historical data is limited or when you want to test against specific market scenarios (e.g., extreme volatility or heavy-tailed distributions).

## Table of Contents
1. [Generating Synthetic Stock Data (Daily)](#generating-synthetic-stock-data-daily)
2. [Generating Synthetic Intraday Data](#generating-synthetic-intraday-data)
3. [Market Scenarios](#market-scenarios)
4. [Custom Distributions and Jumps](#custom-distributions-and-jumps)
5. [Generating Correlated Data](#generating-correlated-data)
6. [Walk-Forward Analysis](#walk-forward-analysis)
7. [Stateful Market Generators (Ticks & Quotes)](#stateful-market-generators-ticks--quotes)

---

## Generating Synthetic Stock Data (Daily)

The `generate_synthetic_stock_data` function creates realistic daily OHLCV paths using Geometric Brownian Motion (GBM) as the default engine.

### Basic Usage
```python
from fastbt.simulation import generate_synthetic_stock_data

# Generate a year of neutral daily data
df = generate_synthetic_stock_data(
    start_date="2024-01-01",
    end_date="2024-12-31",
    initial_price=150.0
)

print(df.head())
```

### Bullish and Bearish Scenarios
You can quickly simulate different market regimes using the `scenario` parameter:

```python
# Generate a bullish scenario
df_bull = generate_synthetic_stock_data(scenario="bullish", mu_bull=0.20)

# Generate a bearish scenario
df_bear = generate_synthetic_stock_data(scenario="bearish", mu_bear=-0.15)
```

---

## Generating Synthetic Intraday Data

The `generate_synthetic_intraday_data` function is designed for granular testing. It handles session hours, overnight gaps, and frequency scaling.

### Stock Session (e.g., NYSE)
```python
from fastbt.simulation import generate_synthetic_intraday_data

# 5-minute bars for a specific trading session
df_intraday = generate_synthetic_intraday_data(
    start_date="2025-01-01",
    end_date="2025-01-05",
    freq="5min",
    start_hour=9.5,  # 9:30 AM
    end_hour=16.0,   # 4:00 PM
    continuous=False
)
```

### Continuous Markets (e.g., Crypto)
For markets that never sleep, use `continuous=True`:

```python
df_crypto = generate_synthetic_intraday_data(
    start_date="2025-01-01",
    freq="1H",
    continuous=True
)
```

---

## Market Scenarios

Both daily and intraday generators support three primary scenarios:
- **`bullish`**: High drift, standard volatility.
- **`bearish`**: Negative drift, typically higher volatility.
- **`neutral`**: Low drift, standard volatility.

You can customize the drift (`mu`) and volatility (`sigma`) for each scenario using arguments like `mu_bull`, `sigma_bear`, etc.

---

## Custom Distributions and Jumps

Standard GBM assumes normal returns. To simulate "black swans" or fat-tailed markets, you can pass custom distributions or empirical data.

### Heavy-Tailed Returns (Student-t)
```python
from scipy.stats import t
import numpy as np

# Student-t with 3 degrees of freedom for fat tails
t_dist = t(df=3, loc=0, scale=0.015)

df = generate_synthetic_stock_data(distribution=t_dist)
```

### Simulating Price Jumps
Enable random price jumps to test stop-loss slippage or gap risk:

```python
df = generate_synthetic_stock_data(
    jump_prob=0.01,   # 1% chance of a jump per day
    jump_scale=3.0    # Jumps are 3x the standard volatility
)
```

---

## Generating Correlated Data

If you need to simulate a portfolio of stocks that move together, use `generate_correlated_data`.

```python
from fastbt.simulation import generate_correlated_data

# Generate 3 columns with [0.8, 0.5, -0.2] correlation to a reference stock
df_portfolio = generate_correlated_data(
    correlations=[0.8, 0.5, -0.2],
    n_samples=252
)

# Returns a DataFrame with columns: ['reference', 'var_1', 'var_2', 'var_3']
```

---

## Walk-Forward Analysis

The `walk_forward` function helps you validate if a parameter that performed well in the past continues to perform well in the future (out-of-sample).

```python
from fastbt.simulation import walk_forward
import numpy as np

# Select the top 1 parameter configuration from last year to use this year
results = walk_forward(
    data=backtest_results_df,
    period='Y',               # Walk forward annually
    parameters=['sma_period', 'rsi_threshold'],
    column='net_profit',      # Ranking metric
    function=np.sum,          # Aggregate profit for the year
    num=1                     # Pick the single best
)
```

---

## Stateful Market Generators (Ticks & Quotes)

For event-driven testing, `fastbt` provides infinite generators that yield data one "tick" at a time. These support two primary modes: **Time-Based** (realistic GBM) and **Sequence-Based** (IID steps).

### Time-Based Mode (`mode='time'`)
This mode uses continuous time math (GBM). Price movement depends on the time elapsed between ticks.

| Parameter | Description |
| :--- | :--- |
| `vol` | Annualized volatility (default 0.2). |
| `intensity` | Average ticks per second (Poisson arrival). |
| `seconds_per_year` | Override the year length (e.g., set to trading hours for NYSE). |
| `vol_multiplier` | Quick scalar to boost price action without changing annual vol. |

```python
from fastbt.simulation import tick_generator

# NYSE Session: 6.5 hours/day, 2x volatility boost for active simulation
gen = tick_generator(
    initial_price=100.0,
    mode='time',
    seconds_per_year=252 * 6.5 * 3600,
    vol_multiplier=2.0
)
tick = next(gen)
```

### Sequence-Based Mode (`mode='sequence'`)
This mode ignores elapsed time for price movement. Every `next()` call results in a new draw from a distribution.

| Parameter | Description |
| :--- | :--- |
| `distribution` | A Scipy distribution (returning multipliers). Defaults to `lognorm(s=0.01)`. |
| `time_multiplier` | Scaler for the wall-clock timestamp (e.g., 60 for "1 real sec = 1 sim min"). |
| `start_time` | Custom starting Timestamp. |

```python
from scipy.stats import norm
from fastbt.simulation import tick_generator

# Pure random walk: Every tick is an IID move from a normal distribution
gen = tick_generator(
    initial_price=100.0,
    mode='sequence',
    distribution=norm(loc=1.0, scale=0.01), # Simple multipliers
    time_multiplier=3600 # Track time at 3600x real speed
)

# Update the distribution halfway through
gen.send({'distribution': norm(loc=1.005, scale=0.05)})
```

### Common Output Schema
Both generators return a dictionary:
```python
{
    'timestamp': pd.Timestamp,
    'price': float,      # Snapped to tick_size
    'size': int,
    'raw_price': float,  # Original high-precision price
    'bid': float,        # (quote_generator only)
    'ask': float         # (quote_generator only)
}
```
