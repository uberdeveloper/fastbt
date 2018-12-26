# Introduction

**fastbt** is a simple and dirty way to do backtests based on end of day data, especially for day trading.
The main purpose is to provide a simple framework to weed out bad strategies so that you could test and improve your better strategies further.

It is based on the assumption that you enter into a position based on some pre-defined rules for a defined period and exit either at the end of the period or when stop loss is triggered. See the [rationale](https://github.com/uberdeveloper/fastbt/blob/master/docs/rationale.md) for this approach and the built-in assumptions. _fastbt is rule-based and not event-based._

If your strategy gets you good results, then check them with a full featured backtesting framework such as [zipline](http://www.zipline.io/) or [backtrader](https://www.backtrader.com/) to verify your results.
If your strategy fails, then it would most probably fail in other environments.

This is **alpha**

Most of the modules are stand alone and you could use them as a single file. See embedding for more details

# Features

-   Create your strategies in Microsoft Excel
-   Backtest as functions so you can parallelize
-   Try different simulations
-   Run from your own datasource or a database connection.
-   Run backtest based on rules
-   Add any column you want to your datasource as formulas

# Installation

fastbt requires python **>=3.6** and can be installed via pip

```
pip install fastbt
```

# Quickstart

Fastbt assumes your data have the following columns (rename them in case of other names)

-   timestamp
-   symbol
-   open
-   high
-   low
-   close
-   volume

```python
from fastbt.rapid import *
backtest(data=data)
```

would return a dataframe with all the trades.

And if you want to see some metrics

```python
metrics(backtest(data=data))
```

You now ran a backtest without a strategy! By default, the strategy buys the top 5 stocks with the lowest price at open price on each period and sells them at the close price at the end of the period.

You can either specify the strategy by way of rules (the recommended way) or create your strategy as a function in python and pass it as a parameter

```python
backtest(data=data, strategy=strategy)
```

If you want to connect to a database, then

```python
from sqlalchemy import create_engine
engine = create_engine('sqlite:///data.db')
backtest(connection=engine, tablename='data')
```

And to SELL instead of BUY

```python
backtest(data=data, order='S')
```

Let's implement a simple strategy.

> **BUY** the top 5 stocks with highest last week returns

Assuming we have a **weeklyret** column,

```python
backtest(data=data, order='B', sort_by='weeklyret', sort_mode=False)
```

We used sort_mode=False to sort them in descending order.

    If you want to test this strategy on a weekly basis, just pass a dataframe with weekly frequency.

See the Introduction notebook in the examples directory for an in depth introduction.

## Embedding

Since fastbt is a thin wrapper around existing packages, the following files can be used as standalone without installing the fastbt package

-   datasource
-   utils
-   loaders

Copy these files and just use them in your own modules.
