# FastBT LLM Reference Document — Design Spec

**Date:** 2026-04-15
**Status:** Approved
**Output file:** `docs/fastbt_reference.md` (the actual starter doc to be created)

---

## Purpose

A standalone reference document that a user loads at the start of an LLM session (via `@` file reference) when they want to backtest a strategy using the FastBT framework. The LLM reads it once, then composes the appropriate features to implement whatever the user describes — simple to complex strategies, across different variations.

Not a tutorial. Not a narrative. A **discovery surface**: mental model + feature catalog + complete examples.

---

## Target Consumer

The primary reader is an LLM (Claude, GPT, etc.), not a human. The human loads it explicitly — it is not ambient (not in CLAUDE.md or AGENTS.md). The user then describes their strategy in natural language and expects the LLM to produce correct, idiomatic FastBT code.

---

## Format

Single Markdown file. Three sections in fixed order. Dense, LLM-optimized. No prose padding.

---

## Section 1 — Mental Model & Lifecycle

### Content

**Engine overview** (text diagram):
```
DataSource → BacktestEngine → Strategy (per-period lifecycle)
```

**Per-period sequence** (fixed, non-negotiable):
```
1. cache.clear()
2. Load underlying price for all dates in the period
3. strategy._reset_for_new_day()       ← resets state/positions, NOT closed_trades
4. strategy.on_day_start(date, day_ctx) → return False to skip entire period
5. for tick in clock:
     bar_ctx.advance(tick, tick_index)
     strategy.run_one_cycle(tick, bar_ctx)
       IDLE  → can_enter? → on_entry → [try_fill → ACTIVE]
       ACTIVE → on_adjust → on_exit_condition? → on_exit → IDLE or DONE
6. strategy._eod_force_close()          ← always fires, once per period end
7. strategy.on_day_end(bar_ctx)
```

**State machine:**
- `IDLE → ACTIVE` (on successful `try_fill`)
- `ACTIVE → IDLE` (after `on_exit`, if cycles remain)
- `ACTIVE → DONE` (after `on_exit`, last cycle exhausted)
- `max_cycles` controls how many entry-exit cycles per period

**Holding periods** (`period=` argument):
- `"day"` (default) — intraday, force-close each day
- `"expiry"` — group dates by nearest expiry; hold overnight until expiry day
- `N` (int) — group N consecutive trading days into one period

**Key invariants** (things that cause bugs when misunderstood):
1. `try_fill` is all-or-nothing. Returns `None` if any leg has no live price. `on_entry` is retried automatically next tick — no retry logic needed.
2. `closed_trades` accumulates across all days and periods. `positions` resets each period.
3. `ctx.trade_date` = period start date (constant within a period). `ctx.date` = actual date of the current tick (changes at day boundaries in multi-day periods).
4. Tick format: single-day period → `"09:15:00"`. Multi-day period → `"2025-01-02 09:15:00"`. Always use `ctx.time` for time comparisons to stay format-agnostic.
5. EOD force-close fires at end of **period**, not each calendar day. A trade entered Monday in `period="expiry"` survives to Thursday's last tick.
6. `on_entry` is called every tick while state is `IDLE`. Do not guard against repeated calls — the engine handles that.

---

## Section 2 — Feature Catalog

### Organization

Grouped by **user intent**, not by class. Each entry has:
- One-line description of what it does
- Exact signature (no implementation detail)
- 3–5 line code snippet showing real usage

### Feature Groups

**1. Setting up**
- `DuckDBParquetLoader(filepath, extra_columns=None)` — load from Parquet
- `DuckDBVortexLoader(filepath, extra_columns=None)` — load from Vortex (drop-in replacement)
- `BacktestEngine(data_source, transaction_cost_pct, max_cycles, clock, period, info_attributes)`
- `engine.add_strategy(strategy)` + `engine.run(start_date, end_date)`

**2. Entering a trade**
- `can_enter(tick, ctx) -> bool` — entry gate, checked every IDLE tick
- `on_entry(tick, ctx)` — build and submit legs here
- `add(strike, opt_type, side, qty, **kwargs) -> Leg` — absolute strikes (default)
- `relative_strikes = True` + `strike_step = 50` — class attributes for offset mode
  - `add(0, "CE", "SELL")` → ATM CE; `add(1, "CE", "SELL")` → 1-step OTM CE; `add(-1, "PE", "BUY")` → 1-step ITM PE
- `try_fill(List[Leg] or Dict[str, Leg], ctx) -> Optional[Dict[str, Trade]]`
  - List mode: keys auto-generated from instrument name (e.g. `"23600CE"`)
  - Dict mode: user-provided keys (e.g. `{"ce": ..., "pe": ...}`) — required when same instrument appears twice

**3. Monitoring & adjusting**
- `on_adjust(tick, ctx)` — called every ACTIVE tick before exit check
- `unrealized_pnl(ctx) -> float` — MTM across all open positions
- `close_trade(label, tick, tick_index, ctx, reason) -> Optional[Trade]` — close one leg
- `close_all(tick, tick_index, ctx, reason) -> List[Trade]` — close all open positions
- `position_summary -> Dict[str, int]` — e.g. `{"23600CE_SELL": 1}` for quick overview
- `ctx.get_price(instrument_key) -> (price, lag)` — lag=0 live, lag>0 fill-forward, -1 no data
- `ctx.get_bar(instrument_key) -> (ohlcv_dict, lag)` — full OHLCV bar

**4. Exiting**
- `on_exit_condition(tick, ctx) -> bool` — return True to trigger exit
- `on_exit(tick, ctx)` — default closes all; override for partial exits
- `exit_reason` string is recorded on each Trade (use meaningful values: `"SL"`, `"TARGET"`, `"EOD_FORCE"`)

**5. Day-start logic**
- `on_day_start(trade_date, day_ctx) -> bool` — return False to skip entire period
- `day_ctx.get_spot() -> (price, lag)` — underlying at first tick
- `day_ctx.get_atm(step=50) -> int` — ATM strike rounded to step
- `day_ctx.prefetch(Instrument(strike, opt_type))` — warm cache before clock loop starts
- `day_ctx.add_to_cache(key, data)` — load external data (VIX, Greeks, macro)

**6. Multi-period & date-boundary awareness**
- `period="day"` / `"expiry"` / `N` on `BacktestEngine`
- `ctx.is_new_date -> bool` — True when date component of tick changed (day boundary in multi-day periods)
- `ctx.changed(key_fn) -> bool` — generic boundary detector: `ctx.changed(lambda t: t[:2])` for hour boundary
- `ctx.is_last_tick -> bool` — True on last tick before EOD force-close
- `ctx.ticks_remaining -> int` — ticks left in period

**7. Custom external data**
- `day_ctx.add_to_cache("VIX", {"09:15:00": 18.5, ...})` in `on_day_start`
- Then `ctx.get_price("VIX")` in any hook — same API as options, same fill-forward semantics
- Data must be keyed by same tick values as the clock

**8. Multi-cycle re-entry**
- `max_cycles=N` on `BacktestEngine` — strategy resets to IDLE after each `on_exit` until N cycles done
- `self.current_cycle` — 0-indexed, readable in any hook
- Each cycle's trades carry `cycle=N` on the Trade object

**9. Trade metadata**
- `add(..., tag="straddle", strikes_away=2)` — kwargs stored in `Leg.meta`, copied to `trade.metadata` at fill (no prefix)
- `info_attributes=["iv", "delta"]` on `BacktestEngine` — auto-captured from bar data as `entry_iv`, `exit_iv` etc.
- `trade.metadata` is a flat dict, merged into top-level columns by `to_dict()`

**10. Output & analysis**
- `strategy.to_dataframe()` — all trades (open + closed) as flat pandas DataFrame
- `strategy.save_trades(path)` — `.parquet`, `.feather`, or `.csv`
- `PerformanceAnalyzer(strategy.closed_trades).calculate_all_metrics()` — total_pnl, win_rate, max_drawdown, sharpe_ratio, etc.

---

## Section 3 — Complete Strategy Examples

Three inline runnable strategies, chosen to show composition of different features. Each is self-contained with `run()` function.

### Example 1: ATM Short Straddle (baseline)
Shows: minimal required pattern, Dict mode `try_fill`, `on_exit_condition`, `PerformanceAnalyzer`.

Source: `examples/strategies/short_straddle.py`

### Example 2: Iron Condor with 50% profit target
Shows: List mode `try_fill` (auto-keys), 4-leg structure, `on_exit` override, custom `_current_pnl` helper.

Source: `examples/strategies/iron_condor.py`

### Example 3: Relative-strike strangle, held till expiry
Shows: `relative_strikes=True`, `strike_step`, `period="expiry"`, `ctx.is_new_date` for date-boundary logic.

Source: `examples/strategies/short_strangle_relative.py` + `examples/strategies/periods_demo.py`

---

## Maintenance Plan

- **Manual updates** — author updates the doc when the API changes
- **Section 2** is the primary update surface — one entry per feature, easy to add/remove
- **Section 3** grows over time — add new examples inline or reference via `# see examples/strategies/foo.py`
- Doc lives at `docs/fastbt_reference.md` in the repo

---

## Out of Scope

- Skill-based guided workflow (Option C) — revisit once doc is stable and examples accumulate
- Auto-generation from docstrings — revisit in Phase 2
- Multi-strategy engine (not yet in framework)
