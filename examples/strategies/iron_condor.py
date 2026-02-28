"""
Strategy 3: Iron Condor
========================
Sell an OTM strangle AND buy further-OTM wings for defined risk.

Structure (4 legs, 2 spreads):
  SELL  (ATM + 100) CE   ← short call
  BUY   (ATM + 200) CE   ← long call wing  (limits max loss)
  SELL  (ATM - 100) PE   ← short put
  BUY   (ATM - 200) PE   ← long put wing   (limits max loss)

Features demonstrated:
  ✓  List[Leg] mode — auto-generated position keys (instrument.key())
  ✓  User clock   — engine ticks only from 09:15 to 15:20
  ✓  on_exit_condition with a profit target (close at 50% premium decay)
  ✓  close_all() for a clean group exit

Run:
    uv run python examples/strategies/iron_condor.py
"""

from datetime import datetime, timedelta
from typing import Any, List, Optional

import pandas as pd

from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.models import Instrument
from fastbt.backtest.strategy import Strategy

DATA_PATH = "/home/pi/data/q1_2025.parquet"
ENTRY_TIME = "09:20:00"
WING_STEP = 100  # points from ATM for short legs
HEDGE_STEP = 200  # points from ATM for long hedge legs
TARGET_PCT = 0.50  # exit when we've captured 50% of max credit


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    """Generate a 1-minute clock from start to end (inclusive)."""
    fmt = "%H:%M:%S"
    current = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while current <= stop:
        clock.append(current.strftime(fmt))
        current += timedelta(minutes=1)
    return clock


class IronCondor(Strategy):
    """
    4-leg iron condor entered at 09:20 with a 50% profit target.

    Legs are passed as a List — keys are AUTO-GENERATED from instrument.key():
        '23500PE', '23300PE', '23700CE', '23900CE'

    Exit logic:
      - Take profit: combined position PnL >= 50% of max credit collected
      - No stop on the condor itself (defined-risk via wings)
      - EOD force-close as backstop
    """

    def __init__(self) -> None:
        super().__init__(name="IronCondor")
        self._max_credit: float = 0.0  # net credit received at entry

    def on_day_start(self, trade_date: str, ctx: Any) -> bool:
        atm = ctx.get_atm(step=50)
        # Prefetch all four strikes we plan to trade
        for opt_type, strikes in [
            ("CE", [atm + WING_STEP, atm + HEDGE_STEP]),
            ("PE", [atm - WING_STEP, atm - HEDGE_STEP]),
        ]:
            for strike in strikes:
                ctx.prefetch(Instrument(strike, opt_type))
        return True

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return tick >= ENTRY_TIME and not self.positions

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)

        # ── List[Leg] mode — keys auto-generated as instrument.key() ──────────
        legs = [
            self.add(
                atm + WING_STEP, "CE", "SELL"
            ),  # short call  → key: e.g. "23700CE"
            self.add(
                atm + HEDGE_STEP, "CE", "BUY"
            ),  # long call   → key: e.g. "23900CE"
            self.add(
                atm - WING_STEP, "PE", "SELL"
            ),  # short put   → key: e.g. "23500PE"
            self.add(
                atm - HEDGE_STEP, "PE", "BUY"
            ),  # long put    → key: e.g. "23300PE"
        ]

        fill = self.try_fill(legs, ctx)  # <── List mode: auto-keys
        if fill:
            # Net credit = sum of SELL premiums - sum of BUY premiums
            credit = sum(
                t.entry_price if t.side == "SELL" else -t.entry_price
                for t in fill.values()
            )
            self._max_credit = max(credit, 0.0)

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        """Exit when open-position PnL >= 50% of the net credit received."""
        if self._max_credit == 0.0:
            return False

        current_pnl = self._current_pnl(ctx)
        if current_pnl is None:
            return False

        return current_pnl >= self._max_credit * TARGET_PCT

    def on_exit(self, tick: Any, ctx: Any) -> None:
        self.close_all(tick, ctx.tick_index, ctx, reason="TARGET")

    def on_day_end(self, ctx: Any) -> None:
        pass

    # ── Internal helper ────────────────────────────────────────────────────────

    def _current_pnl(self, ctx: Any) -> Optional[float]:
        """Compute unrealised PnL of open positions against latest prices."""
        total = 0.0
        for trade in self.positions.values():
            price, lag = ctx.get_price(trade.instrument)
            if price is None:
                return None  # can't compute — skip this tick
            # SELL profits when price falls; BUY profits when price rises
            multiplier = 1 if trade.side == "SELL" else -1
            total += (trade.entry_price - price) * trade.qty * multiplier
        return total


def print_results(strategy: IronCondor) -> None:
    trades = strategy.closed_trades
    analyzer = PerformanceAnalyzer(trades)
    metrics = analyzer.calculate_all_metrics()

    print("\n" + "=" * 55)
    print(f"  STRATEGY : {strategy.name}")
    print("  PERIOD   : 2025-01-01  →  2025-03-31")
    print("  CLOCK    : 09:15 → 15:20 (user-defined, 1-min)")
    print("=" * 55)
    print(f"  Total trades      : {metrics['total_trades']}")
    print(f"  Total PnL         : {metrics['total_pnl']:>10.2f}")
    if metrics["win_rate"] is not None:
        print(f"  Win rate          : {metrics['win_rate']:.1f}%")
    if metrics["avg_profit"] is not None:
        print(f"  Avg profit        : {metrics['avg_profit']:.2f}")
    if metrics["avg_loss"] is not None:
        print(f"  Avg loss          : {metrics['avg_loss']:.2f}")
    print(f"  Max drawdown      : {metrics['max_drawdown']:.2f}")
    if metrics["sharpe_ratio"] is not None:
        print(f"  Sharpe (trade-lv) : {metrics['sharpe_ratio']:.3f}")
    print("=" * 55)

    # Exit reason breakdown
    from collections import Counter

    reasons = Counter(t.exit_reason for t in trades)
    print("\n  Exit reasons:")
    for reason, count in sorted(reasons.items()):
        print(f"    {reason:<15}: {count}")

    if trades:
        rows = [t.to_dict() for t in trades]
        df = pd.DataFrame(rows)[
            [
                "label",
                "instrument",
                "side",
                "entry_tick",
                "entry_price",
                "exit_tick",
                "exit_price",
                "exit_reason",
                "net_pnl",
            ]
        ]
        print("\nTrade log (first 20 rows):")
        print(df.head(20).to_string(index=False))


def run() -> None:
    loader = DuckDBParquetLoader(DATA_PATH)
    strategy = IronCondor()

    # ── User-defined clock: 09:15 to 15:20, every minute ──────────────────────
    clock = make_clock("09:15:00", "15:20:00")

    engine = BacktestEngine(
        loader,
        transaction_cost_pct=0.05,
        clock=clock,  # <── user clock injected here
    )
    engine.add_strategy(strategy)
    engine.run("2025-01-01", "2025-03-31")

    print_results(strategy)


if __name__ == "__main__":
    run()
