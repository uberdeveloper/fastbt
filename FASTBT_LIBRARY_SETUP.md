# FastBT - Fast Event-Based Backtesting Library

## Quick Setup

```bash
cd $HOME
mkdir -p fastbt/fastbt fastbt/tests fastbt/examples
cd fastbt
```

## File Structure

```
fastbt/
├── pyproject.toml
├── README.md
├── .gitignore
├── fastbt/
│   ├── __init__.py
│   ├── engine.py
│   ├── strategy.py
│   ├── models.py
│   ├── metrics.py
│   ├── costs.py
│   └── data.py
├── tests/
│   ├── __init__.py
│   ├── test_engine.py
│   ├── test_metrics.py
│   └── conftest.py
└── examples/
    └── simple_strategy.py
```

## 1. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "fastbt"
version = "0.1.0"
description = "Fast event-based backtesting engine for options trading"
authors = [{name = "Capital"}]
requires-python = ">=3.10"
dependencies = [
    "pandas>=2.0.0",
    "numpy>=1.24.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

## 2. .gitignore

```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
.venv/
venv/
```

## 3. fastbt/__init__.py

```python
"""FastBT - Fast Event-Based Backtesting Library"""

from fastbt.engine import BacktestEngine
from fastbt.strategy import Strategy
from fastbt.models import Trade
from fastbt.metrics import PerformanceAnalyzer
from fastbt.data import DataSource

__version__ = "0.1.0"
__all__ = ["BacktestEngine", "Strategy", "Trade", "PerformanceAnalyzer", "DataSource"]
```

## 4. fastbt/models.py

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class Trade:
    """Represents a single trade with entry, exit, and PnL tracking."""

    symbol: str
    entry_time: datetime
    entry_price: float
    side: str  # 'BUY' or 'SELL'
    quantity: int

    # Exit information
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # PnL tracking
    gross_pnl: float = 0.0
    transaction_cost: float = 0.0
    net_pnl: float = 0.0

    # Optional: MAE/MFE tracking
    max_drawdown: float = 0.0
    max_profit: float = 0.0

    # Flexible metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def close(self, exit_time: datetime, exit_price: float, reason: str,
              transaction_cost_pct: float = 0.0):
        """Close the trade and calculate PnL."""
        self.exit_time = exit_time
        self.exit_price = exit_price
        self.exit_reason = reason

        # Calculate gross PnL
        multiplier = 1 if self.side == 'BUY' else -1
        self.gross_pnl = (self.exit_price - self.entry_price) * self.quantity * multiplier

        # Calculate transaction costs (entry + exit)
        if transaction_cost_pct > 0:
            entry_cost = abs(self.entry_price * self.quantity * transaction_cost_pct / 100)
            exit_cost = abs(self.exit_price * self.quantity * transaction_cost_pct / 100)
            self.transaction_cost = entry_cost + exit_cost

        # Net PnL
        self.net_pnl = self.gross_pnl - self.transaction_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert trade to dictionary."""
        return {
            'symbol': self.symbol,
            'entry_time': self.entry_time,
            'exit_time': self.exit_time,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'side': self.side,
            'quantity': self.quantity,
            'gross_pnl': self.gross_pnl,
            'transaction_cost': self.transaction_cost,
            'net_pnl': self.net_pnl,
            'exit_reason': self.exit_reason,
            **self.metadata
        }
```

## 5. fastbt/data.py

```python
from abc import ABC, abstractmethod
from typing import List
from datetime import date
import pandas as pd


class DataSource(ABC):
    """Abstract base class for data sources."""

    @abstractmethod
    def get_trading_days(self, start_date: str, end_date: str) -> List[date]:
        """Return list of trading days in the date range."""
        pass

    @abstractmethod
    def get_data_for_date(self, trade_date: date) -> pd.DataFrame:
        """Return all market data for a specific date."""
        pass
```

## 6. fastbt/strategy.py

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import date, datetime
import pandas as pd
from fastbt.models import Trade


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
        self.engine = None  # Injected by BacktestEngine
        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []

    def set_engine(self, engine):
        """Called by engine to inject itself."""
        self.engine = engine

    @abstractmethod
    def on_day_start(self, current_date: date):
        """Called at the start of each trading day."""
        pass

    @abstractmethod
    def on_bar(self, timestamp: datetime, snapshot: pd.DataFrame):
        """
        Called for each timestamp with market snapshot.

        Args:
            timestamp: Current timestamp
            snapshot: DataFrame with all market data for this timestamp
                     Columns: [strike, option_type, open, high, low, close, ...]
        """
        pass

    @abstractmethod
    def on_day_end(self):
        """Called at the end of each trading day."""
        pass

    def enter_trade(self, symbol: str, price: float, side: str, quantity: int,
                    timestamp: datetime, metadata: Optional[Dict[str, Any]] = None) -> Trade:
        """Enter a new trade (executed immediately at given price)."""
        trade = Trade(
            symbol=symbol,
            entry_time=timestamp,
            entry_price=price,
            side=side,
            quantity=quantity,
            metadata=metadata or {}
        )
        self.trades.append(trade)
        self.open_trades.append(trade)
        return trade

    def exit_trade(self, trade: Trade, price: float, timestamp: datetime, reason: str):
        """Exit an existing trade."""
        trade.close(
            exit_time=timestamp,
            exit_price=price,
            reason=reason,
            transaction_cost_pct=self.engine.transaction_cost_pct
        )
        if trade in self.open_trades:
            self.open_trades.remove(trade)
```

## 7. fastbt/engine.py

```python
import logging
import time
from typing import Optional, Dict, Any
from fastbt.strategy import Strategy
from fastbt.data import DataSource
from fastbt.metrics import PerformanceAnalyzer


class BacktestEngine:
    """Event-based backtesting engine."""

    def __init__(self, data_loader: DataSource, transaction_cost_pct: float = 0.1):
        """
        Initialize the backtesting engine.

        Args:
            data_loader: DataSource instance for loading market data
            transaction_cost_pct: Transaction cost as percentage (default 0.1%)
        """
        self.loader = data_loader
        self.transaction_cost_pct = transaction_cost_pct
        self.strategy: Optional[Strategy] = None
        self.results: Dict[str, Any] = {}
        self.logger = logging.getLogger("BacktestEngine")

    def add_strategy(self, strategy: Strategy):
        """Add a strategy to the engine."""
        self.strategy = strategy
        strategy.set_engine(self)

    def run(self, start_date: str, end_date: str):
        """Run backtest over the specified date range."""
        if not self.strategy:
            raise ValueError("No strategy added to engine.")

        trading_days = self.loader.get_trading_days(start_date, end_date)
        self.logger.info(f"Running backtest for {len(trading_days)} days...")

        start_time = time.time()

        for i, trade_date in enumerate(trading_days):
            if i % 50 == 0:
                self.logger.info(f"[{self.strategy.name}] Processing {trade_date} ({i}/{len(trading_days)})")

            # Load data for the day
            day_data = self.loader.get_data_for_date(trade_date)

            if day_data.empty:
                continue

            # Notify strategy
            self.strategy.on_day_start(trade_date)

            # Time loop - group by timestamp for market snapshot
            for timestamp, snapshot in day_data.groupby('timestamp'):
                self.strategy.on_bar(timestamp, snapshot)

            # End of day
            self.strategy.on_day_end()

        elapsed = time.time() - start_time
        self._calculate_statistics(elapsed)

    def _calculate_statistics(self, elapsed_time: float):
        """Calculate and store performance statistics."""
        analyzer = PerformanceAnalyzer(self.strategy.trades)
        self.results = analyzer.calculate_all_metrics()
        self.results['execution_time'] = elapsed_time

        # Print summary
        print("\n" + "="*60)
        print(f"BACKTEST RESULTS: {self.strategy.name}")
        print("="*60)
        print(f"Execution Time:    {elapsed_time:.2f}s")
        print(f"Total Trades:      {self.results['total_trades']}")
        print(f"Net PnL:           {self.results['total_net_pnl']:.2f}")
        print(f"Gross PnL:         {self.results['total_gross_pnl']:.2f}")
        print(f"Transaction Costs: {self.results['total_costs']:.2f}")
        print(f"Win Rate:          {self.results['win_rate']*100:.1f}%")
        print(f"Sharpe Ratio:      {self.results['sharpe_ratio']:.2f}")
        print(f"Max Drawdown:      {self.results['max_drawdown']:.2f}")
        print(f"Profit Factor:     {self.results['profit_factor']:.2f}")
        print("="*60)

    def get_results(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        return self.results
```

## 8. fastbt/metrics.py

```python
import pandas as pd
import numpy as np
from typing import List, Dict, Any
from fastbt.models import Trade


class PerformanceAnalyzer:
    """Calculate comprehensive performance metrics from trades."""

    def __init__(self, trades: List[Trade]):
        self.trades = trades
        self.df = self._trades_to_dataframe()

    def _trades_to_dataframe(self) -> pd.DataFrame:
        """Convert trades to DataFrame for analysis."""
        if not self.trades:
            return pd.DataFrame()

        data = [t.to_dict() for t in self.trades]
        df = pd.DataFrame(data)

        if 'entry_time' in df.columns:
            df['date'] = pd.to_datetime(df['entry_time']).dt.date

        return df

    def calculate_all_metrics(self) -> Dict[str, Any]:
        """Calculate all performance metrics."""
        if self.df.empty:
            return self._empty_metrics()

        return {
            # Basic
            'total_trades': len(self.trades),
            'total_gross_pnl': self.total_gross_pnl(),
            'total_net_pnl': self.total_net_pnl(),
            'total_costs': self.total_transaction_costs(),

            # Win/Loss
            'win_rate': self.win_rate(),
            'profit_factor': self.profit_factor(),
            'avg_win': self.avg_win(),
            'avg_loss': self.avg_loss(),

            # Risk-Adjusted
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'calmar_ratio': self.calmar_ratio(),

            # Drawdown
            'max_drawdown': self.max_drawdown(),

            # Time-based
            'monthly_returns': self.monthly_returns(),
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'total_trades': 0,
            'total_gross_pnl': 0.0,
            'total_net_pnl': 0.0,
            'total_costs': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown': 0.0,
            'monthly_returns': {},
        }

    def total_gross_pnl(self) -> float:
        return self.df['gross_pnl'].sum()

    def total_net_pnl(self) -> float:
        return self.df['net_pnl'].sum()

    def total_transaction_costs(self) -> float:
        return self.df['transaction_cost'].sum()

    def win_rate(self) -> float:
        wins = (self.df['net_pnl'] > 0).sum()
        return wins / len(self.df) if len(self.df) > 0 else 0.0

    def profit_factor(self) -> float:
        wins = self.df[self.df['net_pnl'] > 0]['net_pnl'].sum()
        losses = abs(self.df[self.df['net_pnl'] <= 0]['net_pnl'].sum())
        return wins / losses if losses > 0 else 0.0

    def avg_win(self) -> float:
        wins = self.df[self.df['net_pnl'] > 0]['net_pnl']
        return wins.mean() if len(wins) > 0 else 0.0

    def avg_loss(self) -> float:
        losses = self.df[self.df['net_pnl'] <= 0]['net_pnl']
        return losses.mean() if len(losses) > 0 else 0.0

    def sharpe_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sharpe ratio."""
        if 'date' not in self.df.columns:
            return 0.0

        daily_returns = self.df.groupby('date')['net_pnl'].sum()

        if len(daily_returns) < 2:
            return 0.0

        mean_return = daily_returns.mean()
        std_return = daily_returns.std()

        if std_return == 0:
            return 0.0

        return (mean_return - risk_free_rate) / std_return * np.sqrt(252)

    def sortino_ratio(self, risk_free_rate: float = 0.0) -> float:
        """Calculate annualized Sortino ratio."""
        if 'date' not in self.df.columns:
            return 0.0

        daily_returns = self.df.groupby('date')['net_pnl'].sum()

        if len(daily_returns) < 2:
            return 0.0

        mean_return = daily_returns.mean()
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std()

        if downside_std == 0 or np.isnan(downside_std):
            return 0.0

        return (mean_return - risk_free_rate) / downside_std * np.sqrt(252)

    def max_drawdown(self) -> float:
        """Calculate maximum drawdown."""
        if 'date' not in self.df.columns:
            return 0.0

        daily_pnl = self.df.groupby('date')['net_pnl'].sum()
        cumulative = daily_pnl.cumsum()
        running_max = cumulative.expanding().max()
        drawdown = cumulative - running_max

        return drawdown.min()

    def calmar_ratio(self) -> float:
        """Calculate Calmar ratio (annualized return / max drawdown)."""
        if 'date' not in self.df.columns:
            return 0.0

        daily_pnl = self.df.groupby('date')['net_pnl'].sum()
        total_days = len(daily_pnl)

        if total_days == 0:
            return 0.0

        annualized_return = (daily_pnl.sum() / total_days) * 252
        max_dd = abs(self.max_drawdown())

        return annualized_return / max_dd if max_dd > 0 else 0.0

    def monthly_returns(self) -> Dict[str, float]:
        """Calculate monthly returns."""
        if 'date' not in self.df.columns or self.df.empty:
            return {}

        df_copy = self.df.copy()
        df_copy['month'] = pd.to_datetime(df_copy['date']).dt.to_period('M')
        monthly = df_copy.groupby('month')['net_pnl'].sum()

        return {str(k): v for k, v in monthly.items()}
```

## 9. Installation & Usage

### Install in Development Mode

```bash
cd $HOME/intraday_nifty
uv pip install -e $HOME/fastbt
```

### Update DataLoader to Implement DataSource

```python
# In intraday_nifty/src/data_loader.py
from fastbt.data import DataSource

class DataLoader(DataSource):  # Inherit from DataSource
    # ... existing implementation
```

### Update Strategy Imports

```python
# Old
from src.engine.core import Strategy, Trade

# New
from fastbt import Strategy, Trade
```

### Run Backtest

```python
from fastbt import BacktestEngine
from src.data_loader import DataLoader
from src.strategies.orb_scalper import ORBScalper

# Initialize
loader = DataLoader()
engine = BacktestEngine(data_loader=loader, transaction_cost_pct=0.1)

# Add strategy
strategy = ORBScalper(name="ORB")
engine.add_strategy(strategy)

# Run
engine.run(start_date="2024-01-01", end_date="2025-12-31")

# Get results
results = engine.get_results()
print(f"Sharpe: {results['sharpe_ratio']:.2f}")
```

## 10. MultiStrategyEngine — Running Multiple Strategies With a Shared Cache

### When to use it

Use `MultiStrategyEngine` when you want to run several strategies (or parameter
variants of the same strategy) over the same date range and they share common
instruments. The engine:

- Runs a **single DuckDB query per instrument per day** for instruments prefetched
  by the `cache_warmer` (instead of one query per strategy per day)
- Gives each strategy a **fully isolated deep copy** of that warmed cache so
  no strategy can corrupt another's data
- Preserves the **one engine per strategy** design — each `BacktestEngine` carries
  its own `transaction_cost_pct`, `max_cycles`, `info_attributes`

If you don't provide a `cache_warmer`, the behaviour is identical to running each
`BacktestEngine` independently (same results, same DB call count).

---

### API

```python
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.multi_engine import MultiStrategyEngine, CacheWarmerFn
from fastbt.backtest.context import DayStartContext
from fastbt.backtest.models import Instrument

# 1. Create one BacktestEngine per strategy
e1 = BacktestEngine(ds, transaction_cost_pct=0.05, max_cycles=1)
e1.add_strategy(my_strategy_a)

e2 = BacktestEngine(ds, transaction_cost_pct=0.02, max_cycles=2)
e2.add_strategy(my_strategy_b)

# 2. Optionally define a cache warmer
#    Called ONCE per period; populate via ctx.prefetch() only.
def warmer(trade_date: str, ctx: DayStartContext) -> None:
    ctx.prefetch(Instrument(23400, "CE"))
    ctx.prefetch(Instrument(23400, "PE"))

# 3. Create and run
multi = MultiStrategyEngine(
    engines=[e1, e2],
    cache_warmer=warmer,   # optional
    period="day",          # "day" (default), "expiry", or int
    clock=None,            # auto-derived from NIFTY_SPOT if None
)
multi.run("2024-01-01", "2024-12-31")

# 4. Read results from each strategy directly
for engine in multi.engines:
    s = engine.strategy
    net_pnl = sum(t.net_pnl for t in s.closed_trades)
    print(f"{s.name}: trades={len(s.closed_trades)}, net_pnl={net_pnl:.2f}")
```

**Constraints:**
- All engines must share the **same `DataSource` instance** (enforced by identity check)
- The `cache_warmer` must use `ctx.prefetch()` / `ctx.add_to_cache()` — never call
  `data_source.get_instrument_data()` directly inside the warmer
- `MultiStrategyEngine.clock` governs all strategies; per-engine clocks are ignored

---

### Full Example — ATM Straddle + OTM Strangles

A common use case: backtest one ATM straddle and three OTM strangles at different
strikes, all sharing a 20% combined stop-loss, with transaction costs and max cycles
varying per strategy.

```python
from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.multi_engine import MultiStrategyEngine
from fastbt.backtest.models import Instrument
from fastbt.backtest.strategy import Strategy
from fastbt.backtest.context import DayStartContext


# ── Strategies ────────────────────────────────────────────────────────────────

class ATMStraddle(Strategy):
    """Sells ATM CE + PE at 09:20; exits on 20% combined stop-loss."""

    def can_enter(self, tick, ctx):
        return tick == "09:20:00" and not self.positions

    def on_entry(self, tick, ctx):
        atm = ctx.get_atm()
        self.try_fill([
            self.add(atm, "CE", "SELL"),
            self.add(atm, "PE", "SELL"),
        ], ctx)

    def on_exit_condition(self, tick, ctx):
        total_premium = sum(t.entry_price for t in self.positions.values())
        current_loss  = sum(t.unrealized_pnl(ctx) for t in self.positions.values())
        return -current_loss >= total_premium * 0.20


class OTMStrangle(Strategy):
    """Sells OTM CE + PE at a configurable offset from ATM."""

    def __init__(self, otm_offset: int, **kwargs):
        super().__init__(**kwargs)
        self.otm_offset = otm_offset  # e.g. 200, 300, 400

    def can_enter(self, tick, ctx):
        return tick == "09:20:00" and not self.positions

    def on_entry(self, tick, ctx):
        atm = ctx.get_atm()
        self.try_fill([
            self.add(atm + self.otm_offset, "CE", "SELL"),
            self.add(atm - self.otm_offset, "PE", "SELL"),
        ], ctx)

    def on_exit_condition(self, tick, ctx):
        total_premium = sum(t.entry_price for t in self.positions.values())
        current_loss  = sum(t.unrealized_pnl(ctx) for t in self.positions.values())
        return -current_loss >= total_premium * 0.20


# ── Data source ───────────────────────────────────────────────────────────────

ds = DuckDBParquetLoader("data/nifty_options.parquet")


# ── Cache warmer ──────────────────────────────────────────────────────────────
# Pre-fetches ATM ±400 in 50-point steps ONCE per trading day.
# All four strategies deepcopy this data at zero additional DB cost.
# Lazy-fetched strikes (if any strategy goes further OTM) are still
# fetched independently per strategy from the DB.

def warm_atm_range(trade_date: str, ctx: DayStartContext) -> None:
    spot = ctx.get_spot()
    atm  = round(spot / 50) * 50
    for offset in range(-400, 450, 50):
        ctx.prefetch(Instrument(atm + offset, "CE"))
        ctx.prefetch(Instrument(atm + offset, "PE"))


# ── Per-strategy engines ───────────────────────────────────────────────────────
# Each engine carries its own settings; strategies read them at runtime.

engines = []

# ATM straddle — lower cost, 1 entry per day
e_atm = BacktestEngine(ds, transaction_cost_pct=0.03, max_cycles=1)
e_atm.add_strategy(ATMStraddle(name="atm_straddle"))
engines.append(e_atm)

# OTM strangles at 200 / 300 / 400 points — slightly higher cost, up to 2 re-entries
for offset in [200, 300, 400]:
    e = BacktestEngine(ds, transaction_cost_pct=0.05, max_cycles=2)
    e.add_strategy(OTMStrangle(offset, name=f"strangle_{offset}"))
    engines.append(e)


# ── Run ───────────────────────────────────────────────────────────────────────

multi = MultiStrategyEngine(engines, cache_warmer=warm_atm_range)
multi.run("2024-01-01", "2024-12-31")


# ── Results ───────────────────────────────────────────────────────────────────

print(f"\n{'Strategy':<20} {'Trades':>6} {'Net PnL':>12} {'Avg/Trade':>12}")
print("-" * 52)
for engine in multi.engines:
    s         = engine.strategy
    trades    = s.closed_trades
    net_pnl   = sum(t.net_pnl for t in trades)
    avg_trade = net_pnl / len(trades) if trades else 0.0
    print(f"{s.name:<20} {len(trades):>6} {net_pnl:>12.2f} {avg_trade:>12.2f}")
```

**Expected DB call pattern** (with `warm_atm_range`):

```
warm_atm_range     → 1 × 16 strikes × 2 types = 32 DB calls per day
strategy prefetch  → 0 DB calls per strategy (already in deepcopy)
OTM lazy fetch     → 1 DB call per strategy IF it goes further OTM
total per day      ≈ 32  (vs 128 without warmer: 4 strategies × 32)
```

---

### Cache isolation guarantee

Each strategy receives a `copy.deepcopy()` of the warmed cache. Objects at every
nesting level are independent:

```
_warm_cache["23400CE"]["09:15:00"]["close"]   ← warmer's master copy

deepcopy → s_cache_A["23400CE"]["09:15:00"]["close"]   ← strategy A's own copy
deepcopy → s_cache_B["23400CE"]["09:15:00"]["close"]   ← strategy B's own copy

Mutating s_cache_A leaves s_cache_B and _warm_cache unchanged.
```

Only prefetches placed in the `cache_warmer` are shared.
Any `ctx.prefetch()` call inside a strategy's `on_day_start` is private to that
strategy and NOT shared with others.

---

## Next Steps


1. Create the directory structure
2. Copy all files from this document
3. Install in editable mode: `uv pip install -e $HOME/fastbt`
4. Update one strategy as proof-of-concept
5. Validate results match old engine
6. Migrate remaining strategies

## Notes

- Transaction costs applied on both entry and exit
- All metrics calculated on net PnL (after costs)
- Sharpe/Sortino ratios are annualized (252 trading days)
- Engine logs progress every 50 days
- DataLoader must implement `DataSource` protocol
