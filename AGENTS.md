# FastBT Refactoring: Objectives & Architecture Blueprint

## Core Objectives
1. **Speed & Reliability**: Build an ultra-fast, robust, event-based options backtester.
2. **Memory Efficiency**: Handle large tick/minute parquet datasets using DuckDB lazy fetches without preloading all strikes.
3. **No Look-Ahead Bias**: The engine clock controls all data access. Future data is in memory but inaccessible via API.
4. **Standardized Interfaces**: Strict protocols for `DataSource`, `Strategy`, and `BacktestEngine`.
5. **Parallelization-Ready**: Isolate strategy state to allow `concurrent.futures` parameter sweeps.

---

## Architecture Reference

> **Full architecture spec**: See `ARCHITECTURE_FINAL.md` (artifact) for the complete Phase 1 design.
> **Deferred items**: See `BACKTEST_TODO.md` (artifact) for Phase 2+ improvements.

---

## Confirmed Decisions (Summary)

| Decision | Resolution |
|---|---|
| Clock | Pure `List[Any]` — timestamps, integers, anything. Auto or user-defined |
| Cache | Full-day fetch always. Self-healing (lazy fetch on miss). Never exposed raw |
| `prefetch()` | Optional performance hint. Docstring: "cache fetches lazily anyway if skipped" |
| Price returns | `(price, lag)` tuple. lag=0 live, lag>0 stale, None/-1 = no data |
| Leg factory | Single `add(strike, opt_type, side, qty=1)` on Strategy base |
| `try_fill` | All-or-nothing. Accepts `List[Leg]` (auto-key) or `Dict[str, Leg]` (user-key) |
| Positions | `Dict[str, Trade]` — keyed open trades. Key freed on close. Collision → ValueError |
| State machine | IDLE → ACTIVE → DONE. `try_fill` owns IDLE→ACTIVE. Per-tick: adjust → exit_check → exit |
| `max_cycles` | Default 1. Cycle resets on `on_exit`. `closed_trades` accumulates across cycles |
| EOD force close | Always fires on last tick. `on_day_end` fires after |
| `on_day_start` | Gets `DayStartContext` (restricted: spot, atm, prefetch only). Returns False to skip day |
| `BarContext` | Created once/day, mutated per tick. Tick-bound accessors only. No raw cache |

---

## Design Constraints
- **No Numba / preloaded NumPy arrays** in the event engine.
- **Pure Python dicts** for engine state and data points at any bar.
- **Lazy evaluation**: DuckDB queries only when needed (or voluntarily prefetched).
- **Never fetch the same instrument twice** for the same day (cache is the guard).

---

## Known Issues / Lessons Learned
- Prototype (`dummy_engine.py`) validated: DuckDB lazy fetches <20ms; cache lookups nanoseconds.
- Old design used underlying price dict as the loop clock — now separated (clock ≠ data).
- `preload` renamed to `prefetch` to prevent misunderstanding it as a required step.
- `FilledEntry` wrapper class was removed — `try_fill` returns `Optional[Dict[str, Trade]]` directly.
