---

name: load-data
description: Ultra-fast data discovery and loading skill for industrial finance datasets. Handles CSV, JSON, DuckDB, Parquet, and Feather with memory-efficient 2-step discovery and loading.
license: MIT
metadata:
  version: "1.0"
  capabilities: ["CSV", "JSON", "DuckDB", "Parquet", "Feather", "Bulk Loading"]
---

# Load Data Skill

This skill provides a robust framework for importing data from disparate sources into a clean, analysis-ready format. It is designed to be standalone and high-performance.

## Instructions for Agents (Discovery & Inference)
> **Mandatory Discovery Step**: If the user provides a data file but does not specify its structure, schema, or contents, you **MUST** first use the `peek_file` capability to extract the first 5 rows. Send this sample to the LLM context to infer the data schema, column types, and general structure before attempting any full load or complex analysis.

## Capabilities

- **Bulk Multi-Format Collation**: Efficiently merge multiple CSV, Parquet, or Feather files from a directory.
- **DuckDB Integration**: Native support for searching and reading DuckDB databases in read-only mode.
- **JSON Normalization**: Flatten nested JSON structures for tabular analysis.
- **Automated Type Inference**: Intelligent parsing of dates and numeric types with epoch correction for modern data datasets (post-2000).
- **Industrial Memory Safety**: Forced chunked loading for files > 100MB and strict size-based collation guards.
- **Automatic Column Cleaning**: Standardizes column names by default (lowercase, strip non-printable, spaces to underscores, valid Python identifiers for attribute access).

## Usage

### 1. Multi-File Collation
Merge multiple files into a single DataFrame. Supports CSV, Parquet, and Feather. Operation is only performed if total size is **< 100MB**.

```python
from fastbt.loaders import collate_data

# Merge all small historical CSVs
df = collate_data(directory="./history", pattern="*.csv")

# Merge parquet partitions
df_p = collate_data(directory="./partitions", pattern="*.parquet")
```

### 2. Normalized JSON Loading
Convert complex JSON logs into a flat structure.

```python
from fastbt.loaders import normalize_json

data = [
    {"id": 1, "meta": {"time": "2023-01-01", "val": 10}},
    {"id": 2, "meta": {"time": "2023-01-02", "val": 20}}
]
df = normalize_json(data)
# Resulting columns: id, meta_time, meta_val
```

## Flexible Data Workflow
This skill supports both data discovery and full data loading. These can be used independently, or combined for a complete end-to-end pipeline.

### 1. Data Discovery
Use this when you want to understand the structure, schema, or contents of a data file without committing to a full load. This is especially useful for large files or unknown datasets.

- **Sample Inspection**: Uses high-speed CLI tools (where possible) or specialized readers to extract a small sample.
- **DuckDB Discovery**: When peeking at a `.duckdb` or `.db` file, it lists all available tables and returns a sample from the first one.
- **Metadata Awareness**: If accompanying metadata is available (e.g., schemas, column descriptions), the discovery step can incorporate this information.

```python
from fastbt.loaders import peek_file

# Rapid discovery (head-based for text files)
df_sample = peek_file("potential_dataset.csv")

# DuckDB discovery: lists tables and peeks at the first one
df_db_sample = peek_file("market_data.duckdb")
```

### 2. Full Data Loading
Use this when you are ready to load data into memory or a persistent store. This step includes industrial-grade memory safety and performance optimizations.

- **Memory Efficiency**: Automatically switches to chunked loading for files > 100MB.
- **Read-Only Safety**: Database connections (DuckDB) are strictly **read-only** to prevent accidental mutation of source data.
- **Aggregation**: Merge multiple partitions or files into a single dataset.

```python
from fastbt.loaders import efficient_load, collate_data

# Direct full load with safety guards
df = efficient_load("source_data.parquet")

# DuckDB connection: returns a read-only DuckDB connection object
con = efficient_load("analytics.db")
df_query = con.execute("SELECT * FROM trades").df()

# Process multiple files with an optional transform
df_merged = collate_data(directory="./history", pattern="*.csv")
```

### 3. Combined Pipeline (Discovery + Loading)
In most cases, you will use discovery to infer the schema and then perform a full load with specific parameters (like date column names or data types) identified during discovery.

## Configuration & Overrides
All loading functions apply default column cleaning and datetime conversion. You can override these behaviors by passing keyword arguments:

- `lower` (default: `True`): Convert columns to lowercase.
- `strip_non_printable` (default: `True`): Remove non-printable characters and extra whitespace.
- `replace_spaces` (default: `True`): Replace spaces with underscores.
- `ensure_identifiers` (default: `True`): Ensure column names are valid Python identifiers (attribute access).

```python
# Load without modifying column case or replacing spaces
df = efficient_load("data.csv", lower=False, replace_spaces=False)
```


## Included Scripts

- `fastbt.loaders`: The core module for the loading operations.

## Reference Materials

- `references/DATA_FORMATS.md`: Guide on supported data types and optimization techniques.
