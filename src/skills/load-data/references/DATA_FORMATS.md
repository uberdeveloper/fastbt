# Data Formats and Optimization

## Supported Formats
- **CSV**: Standard comma-separated values. For large files, consider using `chunksize`.
- **JSON**: Nested objects are flattened using `pd.json_normalize`.
- **Parquet**: Recommended for high-performance reading and storage efficiency.

## Optimization Tips
1. **Dtype Specification**: Providing explicit dtypes to `read_csv` can significantly reduce memory usage.
2. **Chunking**: Use `chunksize` for files that exceed available RAM.
3. **Date Parsing**: Pre-parse date columns if the format is consistent to speed up loading.

## Peek Analysis Rules (LLM Friendly)
For fast analysis, this skill implements the following non-destructive reading rules:
- **CSV/ZIP**: Reads precisely the first 5 rows via `nrows=5`.
- **DuckDB**: Automatically lists all tables and peeks at the first one found using `read_only=True`.
- **Pickle**: Skips files larger than 100KB to prevent memory exhaustion and prints a warning.
- **Feedback**: Successive use of these rules is explicitly logged to the console.

## Industrial Rules for Memory Efficiency
- **Chunked Loading**: For files exceeding **100MB**, the skill forces `chunksize=100000`. This returns a generator/iterator instead of a full DataFrame to prevent RAM overflow.
- **Read-Only Database Access**: All DuckDB (`.db`, `.duckdb`) connections are strictly `read_only=True` to ensure safety and system stability during analysis.
- **Multi-File Collation**: Concatenates multiple files (CSV, Parquet, Feather) into a single DataFrame only if their **combined size is < 100MB**. If they exceed this, the operation is blocked to prevent crashing the environment.

## Intelligent Type Inference
- **Automatic Datetime Conversion**: Columns containing keywords like `date`, `timestamp`, `datetime`, or `time` are automatically identified.
- **Native Support Check**: If a column (e.g., from Parquet/Arrow) is already a datetime type, it is left untouched.
- **Epoch Unit Correction**: If a conversion results in dates around the year 1970 (standard epoch), but the data is expected to be post-2000, the skill automatically tries different units (`ms`, `us`, `s`, `ns`) to recover the correct timestamp.
