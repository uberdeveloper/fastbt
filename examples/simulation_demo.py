"""
Simulation Demo for fastbt
-------------------------
This script demonstrates how to generate synthetic market data
for both daily and intraday timeframes.
"""

from fastbt.simulation import (
    generate_synthetic_stock_data,
    generate_synthetic_intraday_data,
    generate_correlated_data,
    tick_generator,
    quote_generator,
)
import matplotlib.pyplot as plt


def run_demo():
    print("1. Generating Bullish Daily Data...")
    daily_df = generate_synthetic_stock_data(
        start_date="2024-01-01",
        end_date="2024-12-31",
        scenario="bullish",
        initial_price=100.0,
        seed=42,
    )
    print(daily_df.head())

    print("\n2. Generating Intraday 5-minute Session Data...")
    intraday_df = generate_synthetic_intraday_data(
        start_date="2025-01-01",
        end_date="2025-01-02",
        freq="5min",
        start_hour=9.5,
        end_hour=16.0,
        seed=42,
    )
    print(intraday_df.head())

    print("\n3. Generating Correlated Pairs...")
    correlated_df = generate_correlated_data(
        correlations=[0.9, -0.7], n_samples=100, seed=42
    )
    print(correlated_df.head())

    print("\n4. Infinite Tick & Quote Generators (Stateful)")
    print("-----------------------------------------------")
    # 4.1 Time Mode: Realistic NYSE Session
    print("4.1 Time Mode (NYSE Simulation, 2x Vol Boost)...")
    t_gen_time = tick_generator(
        initial_price=100.0,
        mode="time",
        vol=0.2,
        seconds_per_year=252 * 6.5 * 3600,
        vol_multiplier=2.0,
        seed=42,
    )
    for _ in range(3):
        print(next(t_gen_time))

    # 4.2 Sequence Mode: Pure IID Steps
    print("\n4.2 Sequence Mode (IID steps, 1% lognorm default)...")
    t_gen_seq = tick_generator(
        initial_price=100.0, mode="sequence", time_multiplier=3600, seed=42
    )
    for _ in range(3):
        print(next(t_gen_seq))

    print("\nUpdating Sequence Distribution mid-stream (0.5% drift, 5% vol)...")
    from scipy.stats import norm

    # We use norm(1.005, 0.05) to multiply the price by a value around 1.005
    t_gen_seq.send({"distribution": norm(loc=1.005, scale=0.05)})
    print(next(t_gen_seq))

    # 4.3 Quote Generator (Time Mode)
    print("\n4.3 Quote Generator (Time Mode, 0.5% spread)...")
    q_gen = quote_generator(initial_price=150.0, mode="time", spread=0.005, seed=42)
    for _ in range(2):
        print(next(q_gen))

    # Visualizing the results
    fig, axes = plt.subplots(3, 1, figsize=(10, 15))

    # Plot Daily
    daily_df.set_index("Date")["Close"].plot(
        ax=axes[0], title="Bullish Daily Price Path"
    )

    # Plot Intraday
    intraday_df.set_index("DateTime")["Close"].plot(
        ax=axes[1], title="5-min Intraday Session"
    )

    # Plot Correlations
    correlated_df.plot(ax=axes[2], title="Correlated Variables (Ref vs Var 1 vs Var 2)")

    plt.tight_layout()
    print("\nDemo results saved to simulation_demo.png")
    plt.savefig("simulation_demo.png")


if __name__ == "__main__":
    run_demo()
