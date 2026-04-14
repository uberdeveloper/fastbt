# FastBT Backtesting Framework — LLM Reference

> Load this file at the start of a session when the user wants to implement or explore a backtesting strategy using FastBT.
> This document is the authoritative reference. Do not guess API shapes — use exactly what is specified here.

---

## 1. Mental Model

FastBT runs a strategy over **periods** (one or more trading dates grouped together). The unit of execution is a period, not a day.

```
DataSource ──► BacktestEngine ──► Strategy (per-period lifecycle)
```

**Per-period execution sequence (fixed, non-negotiable):**
```
1. cache.clear()
2. Load underlying prices for ALL dates in the period
3. strategy._reset_for_new_day()        # resets state + positions; closed_trades is NEVER wiped
4. strategy.on_day_start(date, day_ctx) # return False to skip the entire period
5. for tick in clock:
       bar_ctx.advance(tick, tick_index)
       strategy.run_one_cycle(tick, bar_ctx)
         IDLE   → can_enter? → on_entry → [try_fill succeeds → ACTIVE]
         ACTIVE → on_adjust → on_exit_condition? → on_exit → _handle_cycle_done
6. strategy._eod_force_close()          # always fires at period end, closes all open positions
7. strategy.on_day_end(bar_ctx)
```

**State machine:**
- `IDLE → ACTIVE`: triggered by a successful `try_fill()` inside `on_entry`
- `ACTIVE → IDLE`: after `on_exit()` completes, if `current_cycle < max_cycles - 1`
- `ACTIVE → DONE`: after `on_exit()` completes on the last cycle
- State is `DONE` for the rest of the period — no more entries

**Holding periods (`period=` on `BacktestEngine`):**
- `"day"` (default) — one day per period; force-close fires at end of each trading day
- `"expiry"` — dates grouped by nearest option expiry; positions carry overnight; force-close fires at last tick of expiry day
- `N` (int) — N consecutive trading days per period; force-close fires at last tick of Nth day

**Tick format:**
- Single-day period → simple ticks: `"09:15:00"`
- Multi-day period (`"expiry"` or `N > 1`) → composite ticks: `"2025-01-02 09:15:00"`
- **Always use `ctx.time`** (not raw tick) for time comparisons — returns the time portion regardless of format

---

## 2. Critical Invariants

Violating these produces silent wrong results or infinite loops.

| # | Invariant |
|---|-----------|
| 1 | `try_fill` is **all-or-nothing**. Returns `None` if any leg has no live price (lag > 0). `on_entry` is retried automatically next tick. Write no retry logic. |
| 2 | `closed_trades` accumulates across ALL days and periods. Never cleared. `positions` clears each period. |
| 3 | `ctx.trade_date` = **period start date**, constant within a period. `ctx.date` = actual date of the current tick, changes at day boundaries in multi-day periods. |
| 4 | EOD force-close fires at end of **period**, not each calendar day. A trade entered Monday in `period="expiry"` survives to Thursday's last tick. |
| 5 | `on_entry` is called every tick while state is `IDLE`. Do not guard against repeated calls — the engine handles it. |
| 6 | `get_price` on a missing instrument triggers a lazy DuckDB fetch (with a warning). Call `prefetch()` in `on_day_start` for instruments you know you'll use. |
| 7 | `close_trade` uses fill-forward price for exit (last known price). Acceptable for exits. |

---

## 3. Setup

```python
from fastbt.backtest.data import DuckDBParquetLoader   # Parquet source
from fastbt.backtest.data import DuckDBVortexLoader    # Vortex source (drop-in replacement)
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.strategy import Strategy
from fastbt.backtest.metrics import PerformanceAnalyzer
```

```python
# Parquet (standard)
loader = DuckDBParquetLoader(
    filepath="/data/q1_2025.parquet",
    extra_columns=["iv", "delta"],   # optional: extra columns to fetch alongside OHLCV
)

# Vortex (faster, requires DuckDB >= 1.4.2)
loader = DuckDBVortexLoader("/data/q1_2025.vortex")

engine = BacktestEngine(
    data_source=loader,
    transaction_cost_pct=0.05,       # round-trip cost % of notional per leg (entry + exit)
    max_cycles=1,                    # entry-exit cycles per period (default 1)
    clock=None,                      # List[str] of ticks; None = auto-derive from underlying
    period="day",                    # "day" | "expiry" | int
    info_attributes=["iv", "delta"], # bar columns to auto-capture into trade.metadata
)

engine.add_strategy(strategy)
engine.run("2025-01-01", "2025-03-31")
```

**Custom clock example** (minute-resolution, 09:15 to 15:20):
```python
from datetime import datetime, timedelta

def make_clock(start="09:15:00", end="15:20:00"):
    fmt = "%H:%M:%S"
    t, stop, clock = datetime.strptime(start, fmt), datetime.strptime(end, fmt), []
    while t <= stop:
        clock.append(t.strftime(fmt))
        t += timedelta(minutes=1)
    return clock

engine = BacktestEngine(loader, clock=make_clock())
```

---

## 4. Strategy Skeleton

Subclass `Strategy`. Two abstract methods **must** be implemented: `can_enter` and `on_entry`.

```python
class MyStrategy(Strategy):
    # Optional class attributes for relative strike mode (see Section 6)
    relative_strikes: bool = False
    strike_step: int = 50

    def __init__(self):
        super().__init__(name="MyStrategy")
        # add instance state here

    # ── Required ──────────────────────────────────────────────────────────────

    def can_enter(self, tick, ctx) -> bool:
        """Return True when entry conditions are met. Called every IDLE tick."""
        return ctx.time >= "09:20:00"

    def on_entry(self, tick, ctx) -> None:
        """Build legs and call try_fill. Called when can_enter returns True."""
        atm = ctx.get_atm(step=50)
        self.try_fill({"ce": self.add(atm, "CE", "SELL")}, ctx)

    # ── Optional (all have safe defaults) ─────────────────────────────────────

    def on_day_start(self, trade_date, ctx) -> bool:
        """Called once per period before clock loop. Return False to skip period."""
        return True

    def on_adjust(self, tick, ctx) -> None:
        """Called every ACTIVE tick before exit check. Use for SL monitoring, rolling."""
        pass

    def on_exit_condition(self, tick, ctx) -> bool:
        """Return True to trigger on_exit. Default: False (rely on EOD force-close)."""
        return False

    def on_exit(self, tick, ctx) -> None:
        """Default: close all positions. Override for partial exits."""
        self.close_all(tick, ctx.tick_index, ctx, reason="exit_signal")

    def on_day_end(self, ctx) -> None:
        """Called after EOD force-close. Use for logging."""
        pass
```

---

## 5. Building Legs & Filling Orders

### `add()` — create a Leg

```python
leg = self.add(
    strike,    # int: absolute strike (e.g. 23600) when relative_strikes=False
               #      offset from ATM when relative_strikes=True (see Section 6)
    opt_type,  # "CE" or "PE"
    side,      # "BUY" or "SELL"
    qty=1,     # number of lots
    **kwargs,  # arbitrary metadata copied to trade.metadata at fill (no prefix)
)
```

### `try_fill()` — submit legs, all-or-nothing

```python
# Dict mode: user-provided keys (required when same instrument appears twice)
fill = self.try_fill(
    {"ce": self.add(atm, "CE", "SELL"), "pe": self.add(atm, "PE", "SELL")},
    ctx,
)

# List mode: keys auto-generated from instrument name (e.g. "23600CE")
fill = self.try_fill(
    [self.add(atm + 100, "CE", "SELL"), self.add(atm - 100, "PE", "SELL")],
    ctx,
)

# Return value
if fill:
    # fill is Dict[str, Trade] — same keys as input
    entry_premium = fill["ce"].entry_price + fill["pe"].entry_price
# If fill is None: any leg had no live price. on_entry will be called again next tick.
```

---

## 6. Relative Strike Mode

Set class attributes to enable offset-based strike selection:

```python
class MyStrategy(Strategy):
    relative_strikes = True   # enable offset mode
    strike_step = 50          # step size for ATM rounding and offset

    def on_entry(self, tick, ctx):
        # strike arg is now an offset from ATM, not an absolute price
        # CE offsets go UP, PE offsets go DOWN
        self.try_fill({
            "atm_ce":  self.add(0,  "CE", "SELL"),  # ATM CE
            "atm_pe":  self.add(0,  "PE", "SELL"),  # ATM PE
            "otm_ce":  self.add(1,  "CE", "SELL"),  # ATM + 1*step CE
            "otm_pe":  self.add(1,  "PE", "SELL"),  # ATM - 1*step PE
            "wing_ce": self.add(2,  "CE", "BUY"),   # ATM + 2*step CE (hedge)
            "itm_ce":  self.add(-1, "CE", "BUY"),   # ATM - 1*step CE (ITM)
        }, ctx)
```

Offset formula:
- CE: `absolute_strike = ATM + offset * step`
- PE: `absolute_strike = ATM - offset * step`

---

## 7. Context API

### `BarContext` (available in all hooks except `on_day_start`)

```python
# Spot / ATM
spot, lag = ctx.get_spot()             # underlying price at current tick
atm = ctx.get_atm(step=50)            # ATM strike rounded to step

# Option prices
price, lag = ctx.get_price("23600CE") # close price; lag=0 live, lag>0 fill-forward, -1 no data
bar, lag   = ctx.get_bar("23600CE")   # full OHLCV dict: {"open", "high", "low", "close", "volume"}

# Custom data (loaded via add_to_cache)
vix, lag = ctx.get_price("VIX")       # same API as options

# Tick info
ctx.tick          # current clock value ("09:15:00" or "2025-01-02 09:15:00")
ctx.tick_index    # absolute integer counter (0-based)
ctx.time          # time portion only — always "HH:MM:SS", use this for time comparisons
ctx.date          # date portion of current tick — changes at day boundaries in multi-day periods
ctx.trade_date    # period start date — constant within a period

# Boundary detection
ctx.is_last_tick           # True on last tick before EOD force-close
ctx.ticks_remaining        # int: ticks left after current (0 on last tick)
ctx.is_new_date            # True when date changed from previous tick (multi-day periods)
ctx.changed(lambda t: t[:2])  # True when key_fn result changes tick-to-tick (e.g. hour boundary)

# Cache
ctx.prefetch(Instrument(strike, opt_type))   # warm cache before needed
ctx.add_to_cache("KEY", {"09:15:00": val})  # load external data; must use same tick keys as clock
```

### `DayStartContext` (only in `on_day_start`)

```python
spot, lag = ctx.get_spot()            # underlying at first tick of period
atm = ctx.get_atm(step=50)           # ATM at period open

ctx.prefetch(Instrument(23600, "CE")) # warm cache before clock loop (performance, not required)
ctx.add_to_cache("VIX", vix_dict)    # load external data once per period
```

---

## 8. Managing Positions

```python
# Open positions
self.positions          # Dict[str, Trade] — keyed open trades
self.open_trades        # List[Trade] — same, as a list
self.position_summary   # Dict[str, int] e.g. {"23600CE_SELL": 1} — quick overview

# Close one leg
trade = self.close_trade(
    label="ce",         # key in self.positions
    tick=tick,
    tick_index=ctx.tick_index,
    ctx=ctx,
    reason="LEG_SL",    # recorded on Trade.exit_reason
)  # returns Trade or None if label not found

# Close all legs
closed = self.close_all(tick, ctx.tick_index, ctx, reason="TARGET")

# MTM across all open positions
pnl = self.unrealized_pnl(ctx)   # float; uses fill-forward price; falls back to entry_price

# Lookup closed trades
self.closed_trades                            # List[Trade] — all-time accumulator
self.get_closed_by_label("ce")               # List[Trade] with that label
self.get_closed_by_instrument("23600CE")     # List[Trade] for that instrument
```

---

## 9. Trade Object

```python
trade.label          # str: key it was stored under in positions
trade.instrument     # str: e.g. "23600CE" (Instrument.key())
trade.side           # "BUY" or "SELL"
trade.qty            # int
trade.cycle          # int: 0-indexed cycle counter
trade.trade_date     # str: period start date (stamped at fill)
trade.entry_tick     # clock value at fill
trade.entry_index    # int: absolute tick counter at fill
trade.entry_price    # float
trade.exit_tick      # clock value at close (None if open)
trade.exit_price     # float (None if open)
trade.exit_reason    # str (None if open)
trade.gross_pnl      # float (0.0 if open)
trade.net_pnl        # float: gross_pnl - transaction_cost
trade.metadata       # Dict[str, Any]: leg kwargs + info_attributes (merged flat)
trade.is_open        # bool property
```

`trade.metadata` contains:
- Per-leg kwargs from `add(..., tag="straddle")` → `trade.metadata["tag"] = "straddle"`
- `info_attributes` from engine: `entry_iv`, `exit_iv`, `entry_delta`, `exit_delta`, etc.

---

## 10. Custom External Data

Load any time-series data into the cache and access it via the same `get_price` API:

```python
def on_day_start(self, trade_date, ctx):
    vix_data = my_loader.get_vix(trade_date)  # must be {"09:15:00": 18.5, ...}
    ctx.add_to_cache("VIX", vix_data)          # tick keys must match clock
    return True

def on_adjust(self, tick, ctx):
    vix, lag = ctx.get_price("VIX")           # lag=0 live, >0 fill-forward
    if vix and vix > 20:
        self.close_all(tick, ctx.tick_index, ctx, reason="HIGH_VIX")
```

Rules:
- Keys in the data dict must match tick values used by the clock exactly
- Fill-forward semantics apply automatically if a tick is missing
- `get_price` returns the scalar value; `get_bar` returns a dict (use `get_price` for flat data)
- Call `add_to_cache` in `on_day_start` for best performance; can also be called from any hook

---

## 11. Output & Analysis

```python
# DataFrame of all trades (open + closed), metadata merged as top-level columns
df = strategy.to_dataframe()

# Save to file (format inferred from extension)
strategy.save_trades("trades.parquet")  # recommended
strategy.save_trades("trades.feather")
strategy.save_trades("trades.csv")

# Performance metrics
analyzer = PerformanceAnalyzer(strategy.closed_trades)
metrics = analyzer.calculate_all_metrics()
# Keys: total_trades, total_pnl, winning_trades, losing_trades,
#       win_rate (%), avg_profit, avg_loss, max_drawdown, sharpe_ratio
#       (sharpe is trade-level: mean/std, not annualised)
```

---

## 12. Complete Examples

### Example 1 — ATM Short Straddle (minimal pattern)

Entry at 09:20, SL when combined premium doubles, else EOD.

```python
from typing import Any
from fastbt.backtest.data import DuckDBParquetLoader
from fastbt.backtest.engine import BacktestEngine
from fastbt.backtest.metrics import PerformanceAnalyzer
from fastbt.backtest.strategy import Strategy

class ShortStraddle(Strategy):
    def __init__(self):
        super().__init__(name="ShortStraddle")
        self._entry_premium: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= "09:20:00"

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        fill = self.try_fill(
            {"ce": self.add(atm, "CE", "SELL"), "pe": self.add(atm, "PE", "SELL")},
            ctx,
        )
        if fill:
            self._entry_premium = fill["ce"].entry_price + fill["pe"].entry_price

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        ce_price, _ = ctx.get_price(self.positions["ce"].instrument)
        pe_price, _ = ctx.get_price(self.positions["pe"].instrument)
        if ce_price is None or pe_price is None:
            return False
        return (ce_price + pe_price) >= self._entry_premium * 2.0

loader = DuckDBParquetLoader("/data/q1_2025.parquet")
strategy = ShortStraddle()
engine = BacktestEngine(loader, transaction_cost_pct=0.05)
engine.add_strategy(strategy)
engine.run("2025-01-01", "2025-03-31")

metrics = PerformanceAnalyzer(strategy.closed_trades).calculate_all_metrics()
```

---

### Example 2 — Short Strangle, per-leg stop-loss (`on_adjust`)

Sell OTM strangle; close only the leg that hits 3x. Shows `on_adjust` + `close_trade`.

```python
class ShortStrangle(Strategy):
    def __init__(self):
        super().__init__(name="ShortStrangle")

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= "09:20:00"

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        self.try_fill(
            {
                "ce": self.add(atm + 100, "CE", "SELL"),
                "pe": self.add(atm - 100, "PE", "SELL"),
            },
            ctx,
        )

    def on_adjust(self, tick: Any, ctx: Any) -> None:
        for label in list(self.positions.keys()):
            trade = self.positions[label]
            price, _ = ctx.get_price(trade.instrument)
            if price is not None and price >= trade.entry_price * 3.0:
                self.close_trade(label, tick, ctx.tick_index, ctx, reason="LEG_SL")
```

---

### Example 3 — Iron Condor, 50% profit target (`on_exit` override, List mode)

4-leg structure; exit when MTM reaches 50% of net credit. Shows List `try_fill`, `on_exit` override.

```python
class IronCondor(Strategy):
    def __init__(self):
        super().__init__(name="IronCondor")
        self._max_credit: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= "09:15:00"

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        fill = self.try_fill(
            [                                            # List mode: keys auto from instrument name
                self.add(atm + 100,  "CE", "SELL"),
                self.add(atm + 200,  "CE", "BUY"),
                self.add(atm - 100,  "PE", "SELL"),
                self.add(atm - 200,  "PE", "BUY"),
            ],
            ctx,
        )
        if fill:
            self._max_credit = max(
                sum(t.entry_price if t.side == "SELL" else -t.entry_price for t in fill.values()),
                0.0,
            )

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        if self._max_credit == 0.0:
            return False
        total = 0.0
        for trade in self.positions.values():
            price, _ = ctx.get_price(trade.instrument)
            if price is None:
                return False
            mult = 1 if trade.side == "SELL" else -1
            total += (trade.entry_price - price) * mult
        return total >= self._max_credit * 0.50

    def on_exit(self, tick: Any, ctx: Any) -> None:
        self.close_all(tick, ctx.tick_index, ctx, reason="TARGET")
```

---

### Example 4 — Relative strikes, held till expiry (`relative_strikes`, `period="expiry"`)

Sell 1-step OTM strangle; hold till expiry. Shows relative strike mode and multi-day period.

```python
class StrangleTillExpiry(Strategy):
    relative_strikes = True
    strike_step = 50

    def __init__(self):
        super().__init__(name="StrangleTillExpiry")

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        # Enter only on first tick of the period (expiry week open)
        return ctx.tick_index == 0

    def on_entry(self, tick: Any, ctx: Any) -> None:
        # strike=1 → CE: ATM+50, PE: ATM-50
        self.try_fill(
            {"ce": self.add(1, "CE", "SELL"), "pe": self.add(1, "PE", "SELL")},
            ctx,
        )

loader = DuckDBParquetLoader("/data/q1_2025.parquet")
strategy = StrangleTillExpiry()
engine = BacktestEngine(loader, transaction_cost_pct=0.05, period="expiry")
engine.add_strategy(strategy)
engine.run("2025-01-01", "2025-03-31")
```

---

### Example 5 — Multi-cycle re-entry (`max_cycles`)

Enter straddle, exit on SL, re-enter once (2 cycles per day max).

```python
class RecycleStraddle(Strategy):
    def __init__(self):
        super().__init__(name="RecycleStraddle")
        self._entry_premium: float = 0.0

    def can_enter(self, tick: Any, ctx: Any) -> bool:
        return ctx.time >= "09:20:00"

    def on_entry(self, tick: Any, ctx: Any) -> None:
        atm = ctx.get_atm(step=50)
        fill = self.try_fill(
            {"ce": self.add(atm, "CE", "SELL"), "pe": self.add(atm, "PE", "SELL")},
            ctx,
        )
        if fill:
            self._entry_premium = fill["ce"].entry_price + fill["pe"].entry_price

    def on_exit_condition(self, tick: Any, ctx: Any) -> bool:
        ce_price, _ = ctx.get_price(self.positions["ce"].instrument)
        pe_price, _ = ctx.get_price(self.positions["pe"].instrument)
        if ce_price is None or pe_price is None:
            return False
        return (ce_price + pe_price) >= self._entry_premium * 1.5

engine = BacktestEngine(loader, transaction_cost_pct=0.05, max_cycles=2)
# After first on_exit: state → IDLE, current_cycle=1, positions cleared, can enter again
# After second on_exit: state → DONE, no more entries that day
```

---

## 13. Common Patterns

**Skip a day based on market open:**
```python
def on_day_start(self, trade_date, ctx):
    spot, _ = ctx.get_spot()
    if spot and spot < 22000:
        return False   # skip entire period
    return True
```

**Entry after a time window (not before 09:20):**
```python
def can_enter(self, tick, ctx) -> bool:
    return ctx.time >= "09:20:00"
```

**Exit before EOD (not after 15:00):**
```python
def on_exit_condition(self, tick, ctx) -> bool:
    if ctx.time >= "15:00:00":
        return True    # force exit before EOD
    # ... other conditions
```

**Detect day boundary in multi-day period:**
```python
def on_adjust(self, tick, ctx):
    if ctx.is_new_date:
        # first tick of a new calendar day within the same period
        pass
```

**Prefetch known instruments for performance:**
```python
from fastbt.backtest.models import Instrument

def on_day_start(self, trade_date, ctx):
    atm = ctx.get_atm(step=50)
    ctx.prefetch(Instrument(atm, "CE"))
    ctx.prefetch(Instrument(atm, "PE"))
    return True
```

**Access full OHLCV bar:**
```python
def on_adjust(self, tick, ctx):
    bar, lag = ctx.get_bar("23600CE")
    if bar and lag == 0:
        high = bar["high"]
        volume = bar["volume"]
```

**Read `info_attributes` from metadata:**
```python
# engine = BacktestEngine(loader, info_attributes=["iv"])
# After fill, trade.metadata contains "entry_iv"
# After close, trade.metadata contains "exit_iv"
for trade in strategy.closed_trades:
    print(trade.metadata.get("entry_iv"), trade.metadata.get("exit_iv"))
```

---

## 14. What NOT to do

| Wrong | Right |
|-------|-------|
| Write retry logic when `try_fill` returns `None` | Do nothing — `on_entry` is called again next tick automatically |
| Use raw `tick` for time comparisons in multi-day mode | Use `ctx.time` — always returns `"HH:MM:SS"` |
| Clear `closed_trades` between runs | Never — it's the full history accumulator |
| Access `self.positions` after `close_all` | It's empty — iterate a copy if closing mid-loop |
| Pass the same key twice in Dict mode `try_fill` | Raises `ValueError` — use unique labels |
| Pass duplicate instrument in List mode `try_fill` | Raises `ValueError` — use Dict mode with unique labels |
| Assume `on_day_start`'s `ctx` supports `get_price` | It doesn't — use `BarContext` hooks for price access |
| Assume force-close fires each day in `period="expiry"` | It fires once at end of the expiry period, not daily |
