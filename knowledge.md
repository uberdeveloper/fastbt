# FastBT Knowledge Bank

> Critical gotchas, caveats, and institutional knowledge discovered during development.
> This is NOT documentation — it's a living log of things that bite you if you don't know them.

---

## Project Setup

### Runtime
- **Always use `uv run`**, not `python` or `pytest` directly — e.g., `uv run pytest tests/backtest/ -v`
- This project uses `uv`, NOT `poetry` (CLAUDE.md mentions poetry but that applies to a different project — OMSpy)
- Python 3.13.5 is active on this machine

### Test baseline (as of 2026-03-14)
- 244 tests, all passing: `uv run pytest tests/backtest/ -v`
- Any PR must preserve this — zero regressions on `period="day"` (default)

---

## Architecture Gotchas

### `_trade_date` vs `ctx.date`
- `BarContext._trade_date` = the **period start date** (first date of the period). Set by engine once per period. Exposed via `ctx.trade_date` property. **Never changes within a period.**
- `ctx.date` (new) = the **actual date of the current tick**. For single-day it equals `_trade_date`. For multi-day it changes at each day boundary.
- Strategy code using `ctx.trade_date` will always get the period start — this is backward compatible.

### Tick format depends on period size, not period type
- `len(period_dates) == 1` → simple ticks: `"09:15:00"` (unchanged, backward compatible)
- `len(period_dates) > 1` → composite ticks: `"2025-01-02 09:15:00"`
- `period=1` (int) produces len-1 groups → **same format as `period="day"`** — this is intentional

### `_fetch_and_merge` controls the tick key format
- This is the single place that decides simple vs composite keys
- If `multi_day = len(period_dates) > 1`, keys are prefixed with `"YYYY-MM-DD "`
- Used in both `DayStartContext.prefetch` and `BarContext._lazy_fetch` — must be kept in sync

### `DayStartContext.prefetch` and `BarContext._lazy_fetch` both need `period_dates`
- Currently both call `get_instrument_data(self.trade_date / self._trade_date, ...)` — single date only
- After multi-period change, both must loop over all `period_dates` using `_fetch_and_merge`
- **Critical:** forgetting to update one of them means prefetch and lazy-fetch produce different key formats → cache miss on every tick after prefetch

### NIFTY_SPOT cache key is also merged with composite keys for multi-day
- In `_run_period`, the underlying is merged similarly: `key = f"{d} {time_key}" if multi_day else time_key`
- This is done in the engine, not in `_fetch_and_merge` (underlying is not an instrument)

### `_run_day` → `_run_period` rename
- No existing tests reference `_run_day` by name — confirmed via grep. Safe to remove.
- `_run_period` takes `period_dates: List[str]`, derives `multi_day = len(period_dates) > 1`

### Force close fires at end of PERIOD, not end of each day
- For `period=2`, a trade entered on day 1 can survive to day 2 and is force-closed at the last tick of day 2
- `_eod_force_close` and `on_day_end` are called once per `_run_period` call
- `_reset_for_new_day` is also called once per `_run_period` — state machine resets once per period

### `strategy.trade_date` is set to `period_dates[0]`
- This exposes the period start date to all strategy hooks
- Not changed by the clock loop — intentional

---

## Testing Gotchas

### `populated_cache` fixture uses simple time keys
- `tests/backtest/test_context.py`'s `populated_cache` has keys like `"09:15:00"`
- New `TestBarContextDateTime` tests that test COMPOSITE tick parsing still use this fixture — that's fine because `advance()` doesn't look up the cache
- But if a test both uses composite ticks AND calls `get_price()`, the cache won't have matching keys → always returns `(None, -1)`

### `MockDataSource` in `test_engine.py` returns same data for all dates
- `DATES = ["2025-01-02", "2025-01-03"]` — any date in DATES gets same underlying/option data
- This is intentional for multi-day tests: simple to assert, no date-conditional logic needed
- `FourDayDataSource` in `test_multiperiod.py` uses per-date different prices for realistic scenarios

### `group_by_expiry` must preserve chronological order
- Uses a dict to accumulate groups (insertion-ordered in Python 3.7+)
- Dates are iterated in the order `get_available_dates()` returns them — must be sorted

### Plan's `TestPeriodGrouping` requires a `ds` fixture in `test_engine.py`
- The current `test_engine.py` doesn't have a standalone `ds` fixture at module level (it's class-scoped or inline)
- `test_group_by_expiry` takes `ds` as a parameter — must add `@pytest.fixture def ds()` to `test_engine.py`

### `ctx.changed()` on first tick always returns True because `_prev_tick is None`
- The `advance()` method must set `self._prev_tick = self.tick` BEFORE overwriting `self.tick`
- If reversed, `_prev_tick` always equals `tick` after first call → `changed()` never returns True on first tick

---

## Plan Execution Notes

### Task order is load-bearing
- Tasks 1 & 2 (BarContext additions) must be done before Task 4 (engine uses period_dates in contexts)
- Task 3 (grouping functions) is independent and can be done before or after Tasks 1 & 2
- Task 5 (multiperiod tests) requires Tasks 1–4 all complete

### Worktree recommended
- Use a git worktree for isolation: `uv run pytest` from the worktree root
- Main branch: `master`

### `Union` import needed in engine.py
- The plan notes: "add `Union` to the existing `from typing import` line" before using `Union[str, int]` for the `period` parameter

### DayStartContext signature change is backward compatible
- `period_dates: Optional[List[str]] = None` — all existing call sites pass 3 positional args and still work

### BarContext signature change is backward compatible
- Same: `period_dates: Optional[List[str]] = None` — existing tests construct `BarContext(cache, ds, date, clock)` unmodified
