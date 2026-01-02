"""
Load data to database
"""

import os
import glob
import re
import pandas as pd
from typing import Optional, Any
import subprocess
from io import StringIO


def apply_adjustment(
    df,
    adj_date,
    adj_value,
    adj_type="mul",
    date_col="date",
    cols=["open", "high", "low", "close"],
):
    """
    Apply adjustment to a given stock
    df
        dataframe of the given stock
    adj_date
        date from which the adjustment is
        to be made
    adj_value
        value to be adjusted
    adj_type
        method of adjustment **mul/sub**
        mul means multiply all the values
            such as splits and bonuses
        sub means subtract the values
            such as dividends

    date_col
        date column  on which the adjustment
        is to be applied
    cols
        columns to which the adjustment is to
        be made

    Notes
    -----
    1) You can use negative values to add to the
    stock value by using **adj_type=sub**
    2) Adjustment is applied prior to all dates
    in the dataframe
    3) In case your dataframe has date or
    symbol as indexes, reset them
    """
    df = df.set_index(date_col).sort_index()
    values_on_adj_date = df.loc[adj_date, cols].copy()
    if adj_type == "mul":
        adjusted_values = (df.loc[:adj_date, cols] * adj_value).round(2)
    elif adj_type == "sub":
        adjusted_values = (df.loc[:adj_date, cols] - adj_value).round(2)
    else:
        raise ValueError("adj_type should be either mul or sub")
    df.loc[:adj_date, cols] = adjusted_values
    df.loc[adj_date, cols] = values_on_adj_date
    return df.reset_index()


def convert_to_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Automatically converts columns related to date/time to pandas datetime objects.
    Skips conversion if the column is already datetime-like (e.g., from Parquet/Arrow).
    Handles numpy epoch unit mismatches (ms, us, ns) by checking if dates fall before year 2000.
    """
    date_keywords = ["date", "timestamp", "datetime", "time"]
    for col in df.columns:
        if any(key in col.lower() for key in date_keywords):
            # Skip if already datetime-like
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                continue

            try:
                # Initial conversion attempt
                converted = pd.to_datetime(df[col], errors="coerce")

                # Check for 1970/epoch issues (numpy ms/us/ns conversion artifacts)
                # If we expect data after 2000, and we see 1970, it's likely a unit mismatch
                if not converted.dropna().empty:
                    valid_years = converted.dropna().dt.year
                    if (valid_years < 2000).any() and (valid_years == 1970).any():
                        # Try to correct unit for numeric inputs
                        if pd.api.types.is_numeric_dtype(df[col]):
                            for unit in ["ms", "us", "s", "ns"]:
                                try:
                                    trial = pd.to_datetime(
                                        df[col], unit=unit, errors="coerce"
                                    )
                                    if (
                                        not trial.dropna().empty
                                        and (trial.dropna().dt.year >= 2000).all()
                                    ):
                                        converted = trial
                                        break
                                except Exception:
                                    continue

                df[col] = converted
            except Exception as e:
                print(f"Warning: Could not convert column {col} to datetime: {e}")
    return df


def clean_column_names(
    df: pd.DataFrame,
    lower: bool = True,
    strip_non_printable: bool = True,
    replace_spaces: bool = True,
    ensure_identifiers: bool = True,
) -> pd.DataFrame:
    """
    Cleans column names based on the following rules unless overridden:
    1) Lowercase all column names
    2) Strip extra/non-printable characters
    3) Replace spaces with underscores
    4) Ensure names are valid Python identifiers for attribute access
    """
    new_columns = []
    for col in df.columns:
        name = str(col)

        if strip_non_printable:
            # Strip non-printable characters and extra whitespace
            name = "".join(char for char in name if char.isprintable())
            name = name.strip()

        if lower:
            name = name.lower()

        if replace_spaces:
            name = name.replace(" ", "_")

        if ensure_identifiers:
            # Replace any non-alphanumeric character (except underscore) with underscore
            name = re.sub(r"\W+", "_", name)
            # Ensure it doesn't start with a number (prepend an underscore if it does)
            if name and name[0].isdigit():
                name = "_" + name
            # Strip leading/trailing underscores that might have been created
            name = name.strip("_")
            # If the name becomes empty or starts with a number (after strip), provide a default
            if not name:
                name = "col_" + str(len(new_columns))

        new_columns.append(name)

    df.columns = new_columns
    return df


def peek_file(filename: str, **kwargs) -> Optional[pd.DataFrame]:
    """
    STEP 1: DISCOVERY
    Read the first 5 rows for quick analysis and schema inference.
    Uses CLI tools (head) for text formats for maximum speed.
    """
    print(f"## Discovery Step: Peeking at {filename}")
    print("## Reading data files rule applied: Reading first 5 rows only.")

    # Extract cleaning-specific kwargs
    cleaning_kwargs = {
        k: kwargs.pop(k)
        for k in [
            "lower",
            "strip_non_printable",
            "replace_spaces",
            "ensure_identifiers",
        ]
        if k in kwargs
    }

    # Look for accompanying metadata files
    base = os.path.splitext(filename)[0]
    for meta_ext in [".json", ".yaml", ".yml"]:
        meta_file = base + meta_ext
        if os.path.exists(meta_file):
            print(f"## Discovery Step: Found metadata in {meta_file}")
            try:
                with open(meta_file, "r") as f:
                    print(f"Metadata Content:\n{f.read()}")
            except Exception as e:
                print(f"Could not read metadata: {e}")

    ext = os.path.splitext(filename)[1].lower()

    try:
        # Strategy: Use shell tools for text formats for zero-memory discovery
        if ext in [".csv", ".txt", ".log"]:
            result = subprocess.run(
                ["head", "-n", "6", filename], capture_output=True, text=True
            )
            if result.returncode == 0:
                df = pd.read_csv(StringIO(result.stdout), **kwargs)
                df = clean_column_names(df, **cleaning_kwargs)
                return convert_to_datetime(df)
            df = pd.read_csv(filename, nrows=5, **kwargs)
            df = clean_column_names(df, **cleaning_kwargs)
            return convert_to_datetime(df)

        elif ext == ".zip":
            # For zips, we still need pandas to handle decompression
            df = pd.read_csv(filename, nrows=5, **kwargs)
            df = clean_column_names(df, **cleaning_kwargs)
            return convert_to_datetime(df)

        elif ext == ".parquet":
            import pyarrow.parquet as pq
            import pyarrow as pa

            pf = pq.ParquetFile(filename)
            first_batch = next(pf.iter_batches(batch_size=5))
            df = pa.Table.from_batches([first_batch]).to_pandas()
            df = clean_column_names(df, **cleaning_kwargs)
            return convert_to_datetime(df)

        elif ext in [".db", ".duckdb"]:
            import duckdb

            with duckdb.connect(filename, read_only=True) as con:
                tables = con.execute("SHOW TABLES").fetchall()
                print(f"DuckDB Tables found: {[t[0] for t in tables]}")
                if tables:
                    df = con.execute(f"SELECT * FROM {tables[0][0]} LIMIT 5").df()
                    df = clean_column_names(df, **cleaning_kwargs)
                    return convert_to_datetime(df)
            return None

        elif ext == ".pkl" or ext == ".pickle":
            file_size_kb = os.path.getsize(filename) / 1024
            if file_size_kb > 100:
                print(
                    f"Skipping {filename}: Pickle file size ({file_size_kb:.2f} KB) exceeds 100KB limit."
                )
                return None
            df = pd.read_pickle(filename).head(5)
            df = clean_column_names(df, **cleaning_kwargs)
            return convert_to_datetime(df)

        else:
            df = pd.read_table(filename, nrows=5, **kwargs) if ext == ".txt" else None
            if df is not None:
                df = clean_column_names(df, **cleaning_kwargs)
                return convert_to_datetime(df)
            return None

    except Exception as e:
        print(f"Error during discovery (peek) of {filename}: {e}")
        return None


def efficient_load(filename: str, **kwargs) -> Any:
    """
    STEP 2: FULL DATA LOADING
    Loads the entire file (or iterator) using pandas.
    - Files > 100MB are loaded in chunks.
    - DuckDB databases are accessed in read-only mode.
    """
    print(f"## Full Loading Step: {filename}")

    # Extract cleaning-specific kwargs
    cleaning_kwargs = {
        k: kwargs.pop(k)
        for k in [
            "lower",
            "strip_non_printable",
            "replace_spaces",
            "ensure_identifiers",
        ]
        if k in kwargs
    }

    file_size_mb = os.path.getsize(filename) / (1024 * 1024)
    ext = os.path.splitext(filename)[1].lower()

    if ext in [".db", ".duckdb"]:
        import duckdb

        print(f"Accessing DuckDB {filename} in read_only mode.")
        return duckdb.connect(filename, read_only=True)

    # Use pandas for all full loading as requested
    if file_size_mb > 100 and ext in [".csv", ".txt"]:
        print(
            f"File size {file_size_mb:.2f}MB > 100MB. Loading in chunks of 100k rows."
        )
        return pd.read_csv(filename, chunksize=100000, **kwargs)

    df = None
    if ext == ".csv":
        df = pd.read_csv(filename, **kwargs)
    elif ext == ".parquet":
        df = pd.read_parquet(filename, **kwargs)
    elif ext == ".feather":
        df = pd.read_feather(filename, **kwargs)

    if df is not None:
        df = clean_column_names(df, **cleaning_kwargs)
        return convert_to_datetime(df)
    return None


class DataLoader(object):
    """
    Data Loader class
    """

    def __init__(self, directory, mode="HDF", engine=None, tablename=None):
        """
        Initialize parameters
        directory
            directory to search files
        mode
            HDF/SQL - should be explicitly specified
        engine
            filename in case of HDF
            SQL Alchemy connection string in case of engine
        tablename
            table where data is to be written
        parse dates
            list of columns to be parsed as date
        """
        if mode not in ["SQL", "HDF"]:
            raise TypeError("No mode specified; should be HDF or SQL")
        self.directory = directory
        self.mode = mode
        self.engine = engine
        self.tablename = tablename

    def _initialize_HDF_file(self):
        import hashlib

        hashlib.sha1().hexdigest()
        with pd.HDFStore(self.engine) as store:
            s = pd.Series(["hash" * 2])
            if len(store.keys()) == 0:
                store.append("updated/" + self.tablename, s)

    def _write_to_HDF(self, **kwargs):
        """
        Write data to HDF file
        """
        update_table = "/updated/" + self.tablename
        data_table = "/data/" + self.tablename
        updated_list = []
        with pd.HDFStore(self.engine) as store:
            if update_table in store.keys():
                updated_list = store.get(update_table).values

        if kwargs.get("columns"):
            columns = kwargs.pop("columns")
        else:
            columns = None

        if kwargs.get("parse_dates"):
            parse_dates = kwargs.get("parse_dates")
        else:
            parse_dates = None

        if kwargs.get("postfunc"):
            postfunc = kwargs.pop("postfunc")
        else:
            postfunc = None

        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, **kwargs)
                    df = df.rename(str.lower, axis="columns")
                    if columns:
                        df = df.rename(columns, axis="columns")
                    if not (parse_dates):
                        date_cols = ["date", "time", "datetime", "timestamp"]
                        for c in df.columns:
                            if c in date_cols:
                                df[c] = pd.to_datetime(df[c])
                    if postfunc:
                        df = postfunc(df, file, root)
                    df.to_hdf(
                        self.engine,
                        key=data_table,
                        format="table",
                        append=True,
                        data_columns=True,
                    )
                    # Updating the file data
                    pd.Series([file]).to_hdf(
                        self.engine, key=update_table, format="table", append=True
                    )

    def _write_to_SQL(self, **kwargs):
        """
        Write data to SQL database
        """
        update_table = "updated_" + self.tablename
        data_table = self.tablename
        updated_list = []
        if self.engine.has_table(update_table):
            updated_list = pd.read_sql_table(update_table, self.engine).values

        if kwargs.get("columns"):
            columns = kwargs.pop("columns")
        else:
            columns = None

        if kwargs.get("parse_dates"):
            parse_dates = kwargs.get("parse_dates")
        else:
            parse_dates = None

        if kwargs.get("postfunc"):
            postfunc = kwargs.pop("postfunc")
        else:
            postfunc = None

        # Iterating over the files
        for root, direc, files in os.walk(self.directory):
            for file in files:
                if file not in updated_list:
                    filename = os.path.join(root, file)
                    df = pd.read_csv(filename, **kwargs)
                    df = df.rename(str.lower, axis="columns")
                    if columns:
                        df = df.rename(columns, axis="columns")
                    if not (parse_dates):
                        date_cols = ["date", "time", "datetime", "timestamp"]
                        for c in df.columns:
                            if c in date_cols:
                                df[c] = pd.to_datetime(df[c])
                    if postfunc:
                        df = postfunc(df, file, root)
                    s = pd.Series([file])
                    df.to_sql(
                        data_table,
                        con=self.engine,
                        if_exists="append",
                        index=False,
                        chunksize=1500,
                    )
                    # Updating the file data
                    s.to_sql(
                        update_table,
                        con=self.engine,
                        if_exists="append",
                        index=False,
                        chunksize=1500,
                    )

    def load_data(self, **kwargs):
        """
        Load data into database
        kwargs
        columns
            column names as dictionary
            with key being column name from file
            and value being the column to be renamed
            ```
            {'OPENING': 'open', 'CLOSING': 'close'}
            ```
        parse_dates
            columns to be parsed as list
            If not given, any column with name
            date, datetime, time, timestamp is
            automatically parse
        postfunc
            function to be run after reading the csv file
        kwargs
            Any other arguments to the pandas read_csv function
        """
        if self.mode == "HDF":
            self._write_to_HDF(**kwargs)
        else:
            self._write_to_SQL(**kwargs)

    def apply_splits(
        self,
        directory="adjustments",
        filename="splits.csv",
        symbol="symbol",
        timestamp="date",
    ):
        """
        Apply splits recursively
        By default, only open, high, low, close and volume columns
        are modified
        """

        filename = os.path.join(directory, filename)
        try:
            splits = pd.read_csv(filename, parse_dates=[timestamp])
        except Exception as e:
            print(e)

        if self.mode == "SQL":
            df = pd.read_sql_table(self.tablename, self.engine)
            for i, row in splits.iterrows():
                q = 'symbol == "{sym}"'
                temp = df.query(q.format(sym=row.at[symbol]))
                params = {
                    "adj_date": row.at[timestamp],
                    "adj_value": row.at["from"] / row.at["to"],
                    "adj_type": "mul",
                    "date_col": timestamp,
                    "cols": ["open", "high", "low", "close"],
                }
                temp = apply_adjustment(temp, **params)
                params.update(
                    {"adj_value": row.at["to"] / row.at["from"], "cols": ["volume"]}
                )
                temp = apply_adjustment(temp, **params)
                temp.index = df.loc[df[symbol] == row.at[symbol]].index
                df.loc[temp.index] = temp
            df.to_sql(self.tablename, self.engine, if_exists="replace", index=False)
        elif self.mode == "HDF":
            df = pd.read_hdf(self.engine, "/data/" + self.tablename)
            df.index = range(len(df))
            for i, row in splits.iterrows():
                q = 'symbol == "{sym}"'
                temp = df.query(q.format(sym=row.at[symbol]))
                params = {
                    "adj_date": row.at[timestamp],
                    "adj_value": row.at["from"] / row.at["to"],
                    "adj_type": "mul",
                    "date_col": timestamp,
                    "cols": ["open", "high", "low", "close"],
                }
                temp = apply_adjustment(temp, **params)
                params.update(
                    {"adj_value": row.at["to"] / row.at["from"], "cols": ["volume"]}
                )
                temp = apply_adjustment(temp, **params)
                temp.index = df.loc[df[symbol] == row.at[symbol]].index
                df.loc[temp.index] = temp
            df.to_hdf(
                self.engine,
                key="/data/" + self.tablename,
                format="table",
                data_columns=True,
            )


def normalize_json(data: Any, **kwargs) -> pd.DataFrame:
    """
    STEP 2: FULL DATA LOADING (JSON)
    Flatten nested JSON structures for tabular analysis.
    - Uses pd.json_normalize for flattening.
    - Applies auto-cleaning of column names.
    """
    # Extract cleaning-specific kwargs
    cleaning_kwargs = {
        k: kwargs.pop(k)
        for k in [
            "lower",
            "strip_non_printable",
            "replace_spaces",
            "ensure_identifiers",
        ]
        if k in kwargs
    }

    df = pd.json_normalize(data, **kwargs)
    df = clean_column_names(df, **cleaning_kwargs)
    return convert_to_datetime(df)


def collate_data(
    directory: str,
    pattern: str = "*.csv",
    transform: Optional[callable] = None,
    **kwargs,
) -> Optional[pd.DataFrame]:
    """
    STEP 2: FULL DATA LOADING (Multi-file)
    Collate multiple files using pandas if total size < 100MB.
    Optional 'transform' function can be applied to each individual dataframe.

    directory
        directory with the files.
    pattern
        glob pattern to match files
    transform
        function to be run on each file dataframe.
        Takes (df, filename) as arguments.
    kwargs
        kwargs for the pandas read_csv function (or other readers)
    """
    # Extract cleaning-specific kwargs
    cleaning_kwargs = {
        k: kwargs.pop(k)
        for k in [
            "lower",
            "strip_non_printable",
            "replace_spaces",
            "ensure_identifiers",
        ]
        if k in kwargs
    }

    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None

    total_size_mb = sum(os.path.getsize(f) for f in files) / (1024 * 1024)

    if total_size_mb > 100:
        print(
            f"Total size {total_size_mb:.2f}MB exceeds 100MB limit for collation. Use individual efficient_load."
        )
        return None

    print(
        f"## Full Loading Step (Collate): {len(files)} files. Total size: {total_size_mb:.2f}MB."
    )

    ext = os.path.splitext(files[0])[1].lower()
    dataframes = []

    try:
        for f in files:
            # Always use pandas for loading
            if ext == ".csv":
                df = pd.read_csv(f, **kwargs)
            elif ext == ".parquet":
                df = pd.read_parquet(f, **kwargs)
            elif ext == ".feather":
                df = pd.read_feather(f, **kwargs)
            else:
                continue

            # Apply transformation if provided
            if transform:
                df = transform(df, f)
            dataframes.append(df)

    except Exception as e:
        print(f"Error during collation loading: {e}")
        return None

    if not dataframes:
        return None

    df_final = pd.concat(dataframes, ignore_index=True)
    df_final = clean_column_names(df_final, **cleaning_kwargs)
    return convert_to_datetime(df_final)


def read_file(filename, key=None, directory=None, **kwargs):
    """
    A simple wrapper for all pandas read functions
    filename
        filename to load
    key
        key is the additional information required to load a file.
        * excel file - sheet name
        * hdf file - path to data
        * SQL database - SQL Alchemy engine
    directory
        directory to look for files. This path is appended to the filename.
        Creating a partial function would make things easier by
        speciying only the filename every time instead of the entire path.
    kwargs
        list of keyword arguments for the specific pandas read function
    """
    extensions = {
        "excel": set(["xls", "xlsx"]),
        "csv": set(["csv", "txt", "dat"]),
        "hdf": set(["h5", "hdf", "hdf5"]),
    }
    functions = {"excel": pd.read_excel, "csv": pd.read_csv, "hdf": pd.read_hdf}
    mappers = {}
    for k, v in extensions.items():
        dct = {e: functions[k] for e in v}
        mappers.update(dct)
    ext = filename.split(".")[-1]
    func = mappers[ext]
    if directory:
        filename = os.path.join(directory, filename)
    return func(filename, **kwargs)
