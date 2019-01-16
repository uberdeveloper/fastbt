## Introduction

DataSource is a helper class for common, repetitive tasks in financial domain. Given a dataframe with symbol and timestamp columns, you could apply common financial functions to each symbol with a single line of code.

It is a replacement for otherwise verbose code and a wrapper around pandas.

So, instead of

```python
shift = lambda x: x.shift(1)
dataframe['lag_one'] = dataframe.groupby('symbol')['close'].transform(shift)
```

you could write

```python
dataframe.add_lag(on='close', period=1, col_name='lag_one')
```

### Quick start

Initialize datasource with a data frame

```python
from fastbt.datasource import DataSource
ds = DataSource(df) # df is your dataframe

# Add a one day lag to all the symbols in the dataframe
ds.add_lag(1) # returns the dataframe with lag added

# Access the original dataframe with
ds.data
```

See the example notebook for more details

> DataSource always return a dataframe when you call a method

> DataSource converts all columns into **lower case**.

### General

All helper methods start with `add_` and has the following common arguments

| argument   | description                                                              |
| ---------- | ------------------------------------------------------------------------ |
| `on`       | the column on which the operation is to be performed                     |
| `col_name` | column name                                                              |
| `lag`      | period by which the data is to be lagged after performing the operation. |

See the respective method for more specific arguments.

-   `lag` argument not applicable to `add_lag` and `add_formula`
-   By default, all operations are performed on the **close** column
-   A descriptive column name is automatically added with the exception of `add_formula`

### add_lag

Adds a lag on the specified column.

---

| argument | description                                       |
| -------- | ------------------------------------------------- |
| period   | the lag period; identical to the `shift` function |

To add a forward lag, add a negative number

```python
# Adds the next day close
ds.add_lag(on='close', period=-1)
```

### add_pct_change

Adds a percentage change
| argument | description |
| -------- | ------------------------------------------------- |
| period | period for which percentage change to be added |

```python
# Add the 5 day returns
ds.add_pct_change(period=5)
```

### add_rolling

Add a rolling function to all the symbols in the dataframe

| argument   | description                                                                                           |
| ---------- | ----------------------------------------------------------------------------------------------------- |
| `window`   | window on which the rolling operation would be applied                                                |
| `groupby`  | column by which the rolling operation would be applied. By default, its the **symbol** column.        |
| `function` | function to be applied on the window as a string; accepts all pandas rolling functions and **zscore** |

```python
# Caculate the 30-day rolling median for all symbols
ds.add_rolling(30, function='median')
```

### add_indicator

This requires TA-lib

Add an indicator
|argument|description|
|--------|-----------|
`indicator`|add an indicator|
`period`| period for the indicator|

```python
# Add an 30 day exponential moving average for all the symbols
ds.add_indicator('EMA', period=30)
```

Not all TA-Lib indicators are supported

### add_formula

Add a formula
|argument|description|
|--------|-----------|
`formula`|Add a formula string|

The formula should be a string with columns existing in the dataframe. `add_formula` accepts no other argument other than formula and col_name with col_name being mandatory. The string is evaluated using `df.eval`

```python
ds.add_formula('(open+close)/2', col_name='avgPrice')

```

## How DataSource works

## Caveats
