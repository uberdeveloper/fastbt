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
    # 4.1 Tick Generator
    print("Piling 5 ticks from Tick Generator...")
    t_gen = tick_generator(initial_price=100.0, vol=0.2, seed=42)
    for _ in range(5):
        print(next(t_gen))

    print("\nUpdating volatility to 0.8 mid-stream...")
    # Change parameters on the fly
    print(t_gen.send({"vol": 0.8}))
    print(next(t_gen))

    # 4.2 Quote Generator
    print("\nPulling 3 quotes from Quote Generator (0.5% spread)...")
    q_gen = quote_generator(initial_price=150.0, spread=0.005, seed=42)
    for _ in range(3):
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
