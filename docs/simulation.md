# Simulation and Synthetic Data

The `fastbt.simulation` module provides tools for generating synthetic market data and performing walk-forward analysis. This is essential for testing strategy robustness when historical data is limited or when you want to test against specific market scenarios (e.g., extreme volatility or heavy-tailed distributions).

## Table of Contents
1. [Generating Synthetic Stock Data (Daily)](#generating-synthetic-stock-data-daily)
2. [Generating Synthetic Intraday Data](#generating-synthetic-intraday-data)
3. [Market Scenarios](#market-scenarios)
4. [Custom Distributions and Jumps](#custom-distributions-and-jumps)
5. [Generating Correlated Data](#generating-correlated-data)
6. [Walk-Forward Analysis](walk_forward.md)
7. [Stateful Market Generators (Ticks & Quotes)](#stateful-market-generators-ticks--quotes)

---

## Overview: Which Generator Should You Use?

`fastbt` provides two specialized functions for batch synthetic data generation. Choosing the right one depends on the time horizon of your strategy:

| Function | Best For | Key Features |
| :--- | :--- | :--- |
| **`generate_synthetic_stock_data`** | Daily/Weekly Strategies | Fast, uses business days, simple GBM engine. |
| **`generate_synthetic_intraday_data`** | Day Trading / Intraday | Session hours (e.g. 9:15-3:30), overnight jumps, frequency scaling. |

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

### Advanced: Simulating a Market Recovery
You can use the simulation to test how your strategy handles a pivot. Since the function returns a DataFrame, you can easily stitch different regimes together:

```python
import pandas as pd
from fastbt.simulation import generate_synthetic_stock_data

# 1. Simulate a 3-month crash
crash = generate_synthetic_stock_data(
    start_date="2024-01-01",
    end_date="2024-03-31",
    scenario="bearish",
    initial_price=100
)

# 2. Simulate a recovery starting from the last price of the crash
last_price = crash['Close'].iloc[-1]
recovery = generate_synthetic_stock_data(
    start_date="2024-04-01",
    end_date="2024-12-31",
    scenario="bullish",
    initial_price=last_price
)

# Combine them
market_cycle = pd.concat([crash, recovery]).drop_duplicates(subset='Date')
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
    freq="1h",
    continuous=True
)
```

### Deep Dive: Verifying Intraday Dynamics
When generating intraday data, `fastbt` takes care of scaling volatility and drift to the bar frequency. You can verify the consistency of the generated data by resampling:

```python
from fastbt.simulation import generate_synthetic_intraday_data
import pandas as pd

# 1. Generate 1-minute data for a week
df = generate_synthetic_intraday_data(
    start_date="2024-10-01",
    end_date="2024-10-07",
    freq="1min",
    vol=0.25 # 25% annual volatility
)

# 2. Resample to Daily to check if the path makes sense
df['DateTime'] = pd.to_datetime(df['DateTime'])
daily_resampled = df.set_index('DateTime')['Close'].resample('D').last().dropna()

# 3. Calculate realized annual volatility from 1-min returns
import numpy as np
returns = np.log(df['Close']).diff().dropna()
# (252 days * 6.5 hours * 60 minutes) bars per year
realized_vol = returns.std() * np.sqrt(252 * 6.5 * 60)
print(f"Target Vol: 0.25, Realized Vol: {realized_vol:.2f}")
```

---

## Understanding Intraday Gaps
One of the most powerful features of `generate_synthetic_intraday_data` is how it handles the "Overnight Jump." In real markets, the opening price is rarely the same as the previous day's close.

```python
# Generate 2 days of data
df = generate_synthetic_intraday_data(
    start_date="2025-01-01",
    end_date="2025-01-02",
    freq="15min",
    jump_scale=5.0  # Make the overnight gaps significantly larger
)

# The gap between the last row of Day 1 and first row of Day 2
# is automatically calculated to simulate real market gaps.
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

### Complex Scenario: The "Black Swan" Stock
You can combine custom distributions and jumps to simulate a "fragile" asset that grows steady but has occasional catastrophic drops.

```python
from scipy.stats import t
from fastbt.simulation import generate_synthetic_stock_data

# 1. Use a distribution with a slight positive drift but fat tails
growth_dist = t(df=2.5, loc=0.0005, scale=0.01)

# 2. Add a high probability of large negative jumps (simulating tail risk)
df_risky = generate_synthetic_stock_data(
    distribution=growth_dist,
    jump_prob=0.02,     # 2% chance of a jump
    jump_scale=5.0      # Jumps are massive
)
```

---

## Generating Correlated Data

If you need to simulate a portfolio of stocks that move together, use `generate_correlated_data`.

```python
from fastbt.simulation import generate_correlated_data

# Returns a DataFrame with columns: ['reference', 'var_1', 'var_2', 'var_3']
```

### Advanced: Simulating a Hedged Pair
You can use `generate_correlated_data` to simulate a "Pairs Trading" scenario where you have a lead stock and a follower.

```python
import numpy as np
import pandas as pd
from fastbt.simulation import generate_correlated_data

# 1. Start with a real or synthetic price path for Stock A
stock_a_returns = np.random.normal(0.0001, 0.02, 500)

# 2. Generate Stock B returns with 0.95 correlation to Stock A
df_pair = generate_correlated_data(
    correlations=[0.95],
    reference_data=stock_a_returns,
    n_samples=500
)

# 3. Convert returns to price paths
prices = (1 + df_pair).cumprod() * 100
prices.columns = ['Stock_A', 'Stock_B']

# 4. Inject a temporary 'divergence' (alpha opportunity)
prices.loc[200:250, 'Stock_B'] *= 0.95

# This creates a perfect dataset for testing mean-reversion or hedging logic.
```

---

## Walk-Forward Analysis

The `walk_forward` function helps you validate strategy robustness by shifting optimized parameters from one period into the next.

For a comprehensive guide on robustness testing and out-of-sample validation, see the dedicated **[Walk-Forward Analysis Guide](walk_forward.md)**.

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

### Advanced: Real-Time Strategy Testing
The generator pattern allows you to test logic that reacts *between* ticks. This is impossible with batch DataFrames.

```python
from fastbt.simulation import tick_generator

# Start a generator for a volatile asset
stream = tick_generator(initial_price=150.0, vol=0.6, intensity=10)

position = 0
last_price = 150.0

for _ in range(100):
    tick = next(stream)
    price = tick['price']

    # Simple logic: If price drops 1%, "buy the dip"
    if price < last_price * 0.99:
        position += 1
        print(f"BUY at {price}")

    # If price rallies 2%, "take profit"
    elif price > last_price * 1.02:
        position -= 1
        print(f"SELL at {price}")

    last_price = price
```

---

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
