import argparse
from dummy_engine import IntradayDummyEngine

def main():
    parser = argparse.ArgumentParser(description="Run the dummy backtest engine for specific dates.")
    parser.add_argument("--dates", nargs="+", help="Dates to run the backtest for (YYYY-MM-DD format). If not provided, runs for a default set of dates.")
    parser.add_argument("--data", default="/home/pi/data/q1_2025.parquet", help="Path to the parquet data file.")
    
    args = parser.parse_args()
    
    engine = IntradayDummyEngine(args.data)
    
    if args.dates:
        dates_to_run = args.dates
    else:
        # Get first 3 available dates if none provided
        print("No dates provided, fetching first 3 dates from database...")
        dates_to_run = engine.loader.get_available_dates()
        print(f"Running for: {dates_to_run}")

    for date_str in dates_to_run:
        # Reset engine state for each day if necessary
        # Note: IntradayDummyEngine current implementation keeps cache and other state
        # For a clean run per day, we might want to re-instantiate or clear state
        engine.cache = {}
        engine.open_positions = []
        engine.logs = []
        engine.run_day(date_str)
        print("-" * 40)

if __name__ == "__main__":
    main()
