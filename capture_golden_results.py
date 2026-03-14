"""
Task 0 helper: run all example strategies and dump closed_trades as CSV.
Imports strategy classes directly from examples/strategies/ to avoid duplication.
Output goes to docs/superpowers/plans/golden_<strategy_name>.csv

Run: uv run python capture_golden_results.py
"""

import os
import sys

import pandas as pd

# Path manipulation must happen before project imports — noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "examples", "strategies"))

from fastbt.backtest.data import DuckDBParquetLoader  # noqa: E402
from fastbt.backtest.engine import BacktestEngine  # noqa: E402
import iron_condor as ic_mod  # noqa: E402
import opening_range_momentum as orm_mod  # noqa: E402
import short_straddle as ss_mod  # noqa: E402
import short_strangle as sstr_mod  # noqa: E402
import straddle_with_target as swt_mod  # noqa: E402

OUTPUT_DIR = "docs/superpowers/plans"
DATA_PATH = "/home/pi/data/q1_2025.parquet"
DATE_START = "2025-01-01"
DATE_END = "2025-03-31"


def save_golden(name: str, trades: list) -> None:
    if not trades:
        print(f"  WARNING: {name} — no trades. Skipping.")
        return
    rows = [t.to_dict() for t in trades]
    df = pd.DataFrame(rows)
    path = f"{OUTPUT_DIR}/golden_{name}.csv"
    df.to_csv(path, index=False)
    total_pnl = df["net_pnl"].sum()
    print(f"  {name}: {len(trades)} trades, total PnL = {total_pnl:.2f} → {path}")


if __name__ == "__main__":
    print(f"Loading data from {DATA_PATH}...")
    loader = DuckDBParquetLoader(DATA_PATH)

    print(f"\nRunning 5 strategies ({DATE_START} → {DATE_END})...\n")

    # Short Straddle
    s = ss_mod.ShortStraddle()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(s)
    engine.run(DATE_START, DATE_END)
    save_golden(s.name, s.closed_trades)

    # Short Strangle
    s = sstr_mod.ShortStrangle()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(s)
    engine.run(DATE_START, DATE_END)
    save_golden(s.name, s.closed_trades)

    # Iron Condor
    s = ic_mod.IronCondor()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(s)
    engine.run(DATE_START, DATE_END)
    save_golden(s.name, s.closed_trades)

    # Straddle with Target
    s = swt_mod.StraddleWithTarget()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(s)
    engine.run(DATE_START, DATE_END)
    save_golden(s.name, s.closed_trades)

    # Opening Range Momentum — requires user-defined clock
    s = orm_mod.OpeningRangeMomentum()
    clock = orm_mod.make_clock("09:15:00", "15:20:00")
    engine = BacktestEngine(loader, transaction_cost_pct=0.05, clock=clock)
    engine.add_strategy(s)
    engine.run(DATE_START, DATE_END)
    save_golden(s.name, s.closed_trades)

    print("\nDone. Golden results saved.")
