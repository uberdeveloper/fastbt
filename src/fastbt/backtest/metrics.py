"""
fastbt.backtest.metrics
=======================
PerformanceAnalyzer — basic Phase 1 metrics over a list of closed Trades.

Metrics provided:
  - total_trades      : number of closed trades
  - total_pnl         : sum of net_pnl across all trades
  - winning_trades    : count of trades with net_pnl > 0
  - losing_trades     : count of trades with net_pnl < 0
  - win_rate          : winning_trades / total_trades * 100 (%)
  - avg_profit        : mean net_pnl of winning trades
  - avg_loss          : mean net_pnl of losing trades
  - max_drawdown      : maximum peak-to-trough drawdown of cumulative PnL
  - sharpe_ratio      : mean(pnl) / std(pnl) per trade (trade-level, not annualised)

Phase 2 additions (deferred): annualised Sharpe, Calmar ratio, per-instrument breakdown,
per-cycle metrics, strategy tear-sheet.
"""

import math
from typing import Any, Dict, List, Optional

from fastbt.backtest.models import Trade


class PerformanceAnalyzer:
    """
    Compute performance metrics over a list of closed Trade objects.

    Instantiate after the engine run completes:
        analyzer = PerformanceAnalyzer(strategy.closed_trades)
        metrics = analyzer.calculate_all_metrics()
    """

    def __init__(self, trades: List[Trade]):
        self._trades = trades
        self._pnls: List[float] = [t.net_pnl for t in trades]

    # ─── Core metrics (computed on demand) ───────────────────────────────────

    @property
    def total_trades(self) -> int:
        return len(self._trades)

    @property
    def total_pnl(self) -> float:
        return sum(self._pnls)

    @property
    def winning_trades(self) -> int:
        return sum(1 for p in self._pnls if p > 0)

    @property
    def losing_trades(self) -> int:
        return sum(1 for p in self._pnls if p < 0)

    @property
    def win_rate(self) -> Optional[float]:
        """Percentage of winning trades. None if no trades."""
        if not self._trades:
            return None
        return (self.winning_trades / self.total_trades) * 100.0

    @property
    def avg_profit(self) -> Optional[float]:
        """Mean PnL of winning trades. None if no winners."""
        winners = [p for p in self._pnls if p > 0]
        if not winners:
            return None
        return sum(winners) / len(winners)

    @property
    def avg_loss(self) -> Optional[float]:
        """Mean PnL of losing trades. None if no losers."""
        losers = [p for p in self._pnls if p < 0]
        if not losers:
            return None
        return sum(losers) / len(losers)

    @property
    def max_drawdown(self) -> float:
        """
        Maximum peak-to-trough drawdown of the cumulative PnL equity curve.

        Returns 0.0 for empty or all-profit series.
        Positive value represents the magnitude of the worst drawdown.
        """
        if not self._pnls:
            return 0.0

        max_dd = 0.0
        peak = 0.0
        cumulative = 0.0

        for pnl in self._pnls:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            drawdown = peak - cumulative
            if drawdown > max_dd:
                max_dd = drawdown

        return max_dd

    @property
    def sharpe_ratio(self) -> Optional[float]:
        """
        Trade-level Sharpe: mean(pnl) / std(pnl).

        Returns None if fewer than 2 trades or std is 0 (uniform PnL).
        Note: not annualised — use as a relative ranking metric only.
        """
        n = len(self._pnls)
        if n < 2:
            return None

        mean = sum(self._pnls) / n
        variance = sum((p - mean) ** 2 for p in self._pnls) / (n - 1)

        if variance == 0.0:
            return None

        return mean / math.sqrt(variance)

    # ─── Aggregate report ─────────────────────────────────────────────────────

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """
        Return all metrics as a flat dictionary for logging or reporting.

        Keys are stable across Phase 2 additions — new metrics are added
        without removing existing ones.
        """
        return {
            "total_trades": self.total_trades,
            "total_pnl": self.total_pnl,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "avg_profit": self.avg_profit,
            "avg_loss": self.avg_loss,
            "max_drawdown": self.max_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }
