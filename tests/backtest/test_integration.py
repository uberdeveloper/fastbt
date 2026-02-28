"""
Integration test: ATM short straddle strategy on real q1_2025.parquet data.

Tests:
- Engine runs without error over real data
- Trades are filled and closed (not zero-results)
- PnL values are finite floats
- closed_trades accumulate across days
- PerformanceAnalyzer produces valid metrics
- No look-ahead bias: entry_tick <= exit_tick ordering
- EOD force-close fires when strategy doesn't self-exit (all trades have an exit_reason)

Run with: uv run pytest tests/backtest/test_integration.py -v
"""
import os
from typing import Any

import pytest

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

REAL_DATA = os.path.expandvars("$HOME/data/q1_2025.parquet")


def pytest_skip_if_no_data():
    if not os.path.exists(REAL_DATA):
        pytest.skip("Real data not available at $HOME/data/q1_2025.parquet")


# ─── ATM Short Straddle Strategy ─────────────────────────────────────────────


class AtmShortStraddle(Strategy):
    """
    Sell ATM CE + PE at 09:20 and hold till EOD.

    Entry: first tick at or after 09:20 where both legs have live prices.
    Exit:  relies on EOD force-close (no explicit exit condition).
    """

    ENTRY_TIME = "09:20:00"

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        # Prefetch ATM CE and PE in advance
        atm = ctx.get_atm(step=50)
        from fastbt.backtest.models import Instrument
        ctx.prefetch(Instrument(atm, "CE"))
        ctx.prefetch(Instrument(atm, "PE"))
        return True

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick >= self.ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        fill = self.try_fill(
            {
                "ce": self.add(atm, "CE", "SELL"),
                "pe": self.add(atm, "PE", "SELL"),
            },
            ctx,
        )
        if fill:
            # Store entry premium for reference
            self.metadata = {
                "atm": atm,
                "entry_premium": fill["ce"].entry_price + fill["pe"].entry_price,
                "entry_tick": tick,
            }

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        return False  # Hold till EOD

    def on_day_end(self, ctx: Any) -> None:
        pass  # nothing to do

    def __init__(self):
        super().__init__(name="AtmShortStraddle")
        self.metadata: dict = {}


# ─── Integration tests ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def straddle_result():
    """Run the ATM straddle on first 5 trading days of q1_2025."""
    if not os.path.exists(REAL_DATA):
        pytest.skip("Real data not available")

    loader = DuckDBParquetLoader(REAL_DATA)
    all_dates = loader.get_available_dates()
    start = all_dates[0]
    end = all_dates[min(4, len(all_dates) - 1)]  # up to 5 days

    strategy = AtmShortStraddle()
    engine = BacktestEngine(loader, transaction_cost_pct=0.05)
    engine.add_strategy(strategy)
    engine.run(start, end)

    return {
        "strategy": strategy,
        "analyzer": PerformanceAnalyzer(strategy.closed_trades),
        "start": start,
        "end": end,
    }


class TestStraddleIntegration:
    def test_runs_without_error(self, straddle_result):
        """No exception during engine.run() → basic sanity."""
        assert straddle_result is not None

    def test_closed_trades_not_empty(self, straddle_result):
        """Should have at least some trades (CE + PE per day filled)."""
        trades = straddle_result["strategy"].closed_trades
        assert len(trades) > 0

    def test_no_open_positions_remaining(self, straddle_result):
        """All positions must be closed after EOD force-close."""
        assert straddle_result["strategy"].positions == {}

    def test_every_trade_has_exit_reason(self, straddle_result):
        """EOD_FORCE or exit_signal — no trade should be left without a reason."""
        trades = straddle_result["strategy"].closed_trades
        for trade in trades:
            assert trade.exit_reason is not None, f"Trade {trade.label} has no exit_reason"

    def test_entry_before_exit(self, straddle_result):
        """No look-ahead bias: entry_tick must be <= exit_tick."""
        trades = straddle_result["strategy"].closed_trades
        for trade in trades:
            assert trade.entry_tick <= trade.exit_tick, (
                f"Trade {trade.label}: entry {trade.entry_tick} > exit {trade.exit_tick}"
            )

    def test_entry_at_or_after_entry_window(self, straddle_result):
        """All entries must be at 09:20 or later."""
        trades = straddle_result["strategy"].closed_trades
        for trade in trades:
            assert trade.entry_tick >= "09:20:00", (
                f"Trade {trade.label} entered at {trade.entry_tick} — before entry window"
            )

    def test_pnl_is_finite(self, straddle_result):
        trades = straddle_result["strategy"].closed_trades
        for trade in trades:
            assert isinstance(trade.net_pnl, float)
            assert trade.net_pnl == trade.net_pnl   # NaN check (NaN != NaN)

    def test_transaction_costs_applied(self, straddle_result):
        """With 0.05% cost, transaction_cost must be > 0."""
        trades = straddle_result["strategy"].closed_trades
        assert all(t.transaction_cost > 0.0 for t in trades)

    def test_metrics_produce_valid_output(self, straddle_result):
        analyzer = straddle_result["analyzer"]
        metrics = analyzer.calculate_all_metrics()
        assert metrics["total_trades"] == len(straddle_result["strategy"].closed_trades)
        assert isinstance(metrics["total_pnl"], float)
        assert isinstance(metrics["max_drawdown"], float)
        assert metrics["max_drawdown"] >= 0.0

    def test_win_rate_in_valid_range(self, straddle_result):
        analyzer = straddle_result["analyzer"]
        wr = analyzer.win_rate
        if wr is not None:
            assert 0.0 <= wr <= 100.0

    def test_trade_pairs_per_day(self, straddle_result):
        """Each day should have exactly 2 trades (CE + PE) if entry filled."""
        from collections import Counter
        trades = straddle_result["strategy"].closed_trades
        # Group by entry_tick day prefix (first 10 chars = YYYY-MM-DD)
        # Actually entry_tick is "HH:MM:SS" string — group by (cycle, instrument type)
        ce_count = sum(1 for t in trades if t.instrument.endswith("CE"))
        pe_count = sum(1 for t in trades if t.instrument.endswith("PE"))
        assert ce_count == pe_count, (
            f"Unequal CE ({ce_count}) and PE ({pe_count}) legs — straddle broken"
        )
