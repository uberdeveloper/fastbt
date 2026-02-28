"""
Tests for fastbt.backtest.metrics — PerformanceAnalyzer.
Run with: uv run pytest tests/backtest/test_metrics.py -v

Basic metrics only for Phase 1: total PnL, win rate, max drawdown, Sharpe ratio.
Edge cases: empty trades, single trade, all winners, all losers.
"""
from typing import Any

import pytest

from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.models import Trade


# ─── Helpers ──────────────────────────────────────────────────────────────────


def make_closed_trade(
    label: str = "23600CE",
    instrument: str = "23600CE",
    side: str = "SELL",
    net_pnl: float = 0.0,
    entry_tick: Any = "09:15:00",
    exit_tick: Any = "15:29:00",
    cycle: int = 0,
    entry_price: float = 100.0,
    exit_price: float = 100.0,
) -> Trade:
    """Factory for a pre-closed Trade with controllable PnL."""
    t = Trade(
        label=label,
        instrument=instrument,
        side=side,
        qty=1,
        cycle=cycle,
        entry_tick=entry_tick,
        entry_index=0,
        entry_price=entry_price,
    )
    t.exit_tick = exit_tick
    t.exit_index = 374
    t.exit_price = exit_price
    t.exit_reason = "test"
    gross = (exit_price - entry_price) * (1 if side == "BUY" else -1)
    t.gross_pnl = gross
    t.transaction_cost = 0.0
    t.net_pnl = net_pnl
    return t


def make_trades(pnls):
    """Quick helper: list of closed trades from a list of net_pnl values."""
    return [make_closed_trade(net_pnl=p) for p in pnls]


# ─── PerformanceAnalyzer init ─────────────────────────────────────────────────


class TestInit:
    def test_accepts_empty_list(self):
        analyzer = PerformanceAnalyzer([])
        assert analyzer is not None

    def test_accepts_list_of_trades(self):
        trades = make_trades([100.0, -50.0, 75.0])
        analyzer = PerformanceAnalyzer(trades)
        assert analyzer is not None


# ─── Basic summary metrics ────────────────────────────────────────────────────


class TestSummaryMetrics:
    def test_total_trades_count(self):
        analyzer = PerformanceAnalyzer(make_trades([100, -50, 75]))
        assert analyzer.total_trades == 3

    def test_total_trades_empty(self):
        assert PerformanceAnalyzer([]).total_trades == 0

    def test_total_pnl(self):
        analyzer = PerformanceAnalyzer(make_trades([100.0, -50.0, 75.0]))
        assert analyzer.total_pnl == pytest.approx(125.0)

    def test_total_pnl_empty(self):
        assert PerformanceAnalyzer([]).total_pnl == pytest.approx(0.0)

    def test_total_pnl_all_losers(self):
        analyzer = PerformanceAnalyzer(make_trades([-20.0, -30.0]))
        assert analyzer.total_pnl == pytest.approx(-50.0)

    def test_winning_trades(self):
        analyzer = PerformanceAnalyzer(make_trades([100.0, -50.0, 75.0, -10.0]))
        assert analyzer.winning_trades == 2

    def test_losing_trades(self):
        analyzer = PerformanceAnalyzer(make_trades([100.0, -50.0, 75.0, -10.0]))
        assert analyzer.losing_trades == 2

    def test_win_rate_percent(self):
        """3 wins, 1 loss → 75% win rate."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, 50.0, 75.0, -10.0]))
        assert analyzer.win_rate == pytest.approx(75.0)

    def test_win_rate_zero_when_all_losers(self):
        analyzer = PerformanceAnalyzer(make_trades([-100.0, -50.0]))
        assert analyzer.win_rate == pytest.approx(0.0)

    def test_win_rate_hundred_when_all_winners(self):
        analyzer = PerformanceAnalyzer(make_trades([100.0, 50.0]))
        assert analyzer.win_rate == pytest.approx(100.0)

    def test_win_rate_none_when_empty(self):
        assert PerformanceAnalyzer([]).win_rate is None

    def test_avg_profit(self):
        """Average PnL of winning trades."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, 50.0, -30.0]))
        assert analyzer.avg_profit == pytest.approx(75.0)

    def test_avg_loss(self):
        """Average PnL of losing trades."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, -30.0, -70.0]))
        assert analyzer.avg_loss == pytest.approx(-50.0)

    def test_avg_profit_none_when_no_winners(self):
        assert PerformanceAnalyzer(make_trades([-100.0])).avg_profit is None

    def test_avg_loss_none_when_no_losers(self):
        assert PerformanceAnalyzer(make_trades([100.0])).avg_loss is None


# ─── Max drawdown ─────────────────────────────────────────────────────────────


class TestMaxDrawdown:
    def test_no_drawdown_all_profits(self):
        """Equity curve only rises — drawdown is 0."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, 50.0, 75.0]))
        assert analyzer.max_drawdown == pytest.approx(0.0)

    def test_drawdown_single_loss(self):
        """100, -50 → peak at 100, trough at 50 → drawdown = 50."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, -50.0]))
        assert analyzer.max_drawdown == pytest.approx(50.0)

    def test_drawdown_recovers_then_drops(self):
        """100, -30, 50, -80 → peak at 120, trough at 40 → DD = 80."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, -30.0, 50.0, -80.0]))
        assert analyzer.max_drawdown == pytest.approx(80.0)

    def test_drawdown_empty_trades(self):
        assert PerformanceAnalyzer([]).max_drawdown == pytest.approx(0.0)

    def test_drawdown_all_losers(self):
        """Continuous decline: peak=0, trough=-150."""
        analyzer = PerformanceAnalyzer(make_trades([-50.0, -50.0, -50.0]))
        assert analyzer.max_drawdown == pytest.approx(150.0)


# ─── Sharpe ratio ─────────────────────────────────────────────────────────────


class TestSharpeRatio:
    def test_sharpe_empty_returns_none(self):
        assert PerformanceAnalyzer([]).sharpe_ratio is None

    def test_sharpe_single_trade_returns_none(self):
        """Cannot compute std dev from 1 trade."""
        assert PerformanceAnalyzer(make_trades([100.0])).sharpe_ratio is None

    def test_sharpe_zero_std_returns_none(self):
        """All trades identical → std=0 → avoid divide by zero."""
        assert PerformanceAnalyzer(make_trades([50.0, 50.0, 50.0])).sharpe_ratio is None

    def test_sharpe_positive_for_net_positive(self):
        """Positive mean PnL with some variance → Sharpe > 0."""
        analyzer = PerformanceAnalyzer(make_trades([100.0, 80.0, 90.0, 110.0]))
        assert analyzer.sharpe_ratio > 0.0

    def test_sharpe_negative_for_net_negative(self):
        analyzer = PerformanceAnalyzer(make_trades([-100.0, -80.0, -90.0]))
        assert analyzer.sharpe_ratio < 0.0


# ─── calculate_all_metrics() ──────────────────────────────────────────────────


class TestCalculateAllMetrics:
    def test_returns_dict(self):
        result = PerformanceAnalyzer(make_trades([100.0, -50.0])).calculate_all_metrics()
        assert isinstance(result, dict)

    def test_all_keys_present(self):
        result = PerformanceAnalyzer(make_trades([100.0, -50.0])).calculate_all_metrics()
        expected_keys = {
            "total_trades", "total_pnl", "winning_trades", "losing_trades",
            "win_rate", "avg_profit", "avg_loss", "max_drawdown", "sharpe_ratio",
        }
        assert expected_keys.issubset(result.keys())

    def test_empty_trades_returns_zeros(self):
        result = PerformanceAnalyzer([]).calculate_all_metrics()
        assert result["total_trades"] == 0
        assert result["total_pnl"] == 0.0
        assert result["max_drawdown"] == 0.0
        assert result["sharpe_ratio"] is None
