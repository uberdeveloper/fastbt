# FastBT Refactoring: Objectives & Blueprint

## Core Objectives
1. **Speed & Reliability**: Build an ultra-fast, robust, event-based options backtester.
2. **Memory Efficiency**: Handle large tick/minute parquet datasets using chunked reads (e.g., DuckDB, PyArrow) without blowing up RAM.
3. **No Look-Ahead Bias**: Ensure the engine only exposes data available at the current simulated timestamp.
4. **Standardized Interfaces**: Develop strict protocols for `DataSource`, `Strategy`, and `BacktestEngine`.
5. **Parallelization-Ready**: Isolate strategy states to allow `concurrent.futures` optimization sweeps.

## Design Constraints & Rules
- **Data Loading**: Use `pandas` `nrows=5` or `pyarrow` batch streaming for file discovery. Enforce chunking for large files.
- **Execution Engine (`BacktestEngine`)**
  - **Paradigm shift:** We are explicitly *not* using Numba (`@njit`) or massive preloaded Numpy arrays for this event engine constraint.
  - **Data Structures:** We will use pure Python `dict`s for representing the engine state and data points at any given bar constraint (as dict access is incredibly fast and avoids object instantiations).
  - **Data Fetching:** Lazy evaluation model. We loop through time bounds (e.g., tick by tick from 09:15 to 15:30) checking our conditions. Only when a strategy determines it needs data for a specific option instrument (e.g., ATM Call) do we execute a targeted DuckDB query to pull *just that instrument's data for the remainder of the day*.
  - **Caching:** The results of targeted DuckDB pulls are cached in memory (as dicts). We never fetch the same instrument's data twice for the same day.
3. **Strategy Abstraction (`Strategy`)**
   - Goal: Map user logic to the engine events (`on_bar`).
4. **Execution & PnL (`Trade`, `Metrics`)**
   - Goal: Vectorized or Numba-optimized PnL evaluation.

## Known Issues / Lessons Learned
- *To be populated as development progresses.*
