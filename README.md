# Introduction

**fastbt** is a simple and dirty way to do backtests based on end of day data, especially for day trading.
The main purpose is to provide a simple framework to weed out bad strategies so that you could test and improve your better strategies further.

It is based on the assumption that you enter into a position based on some pre-defined rules for a defined period and exit either at the end of the period or when stop loss is triggered. See the [rationale]for this approach and the built itinassumptions.

If your strategy gets you good results, then check them with a full featured backtesting framework such as [zipline](http://www.zipline.io/) or [backtrader](https://www.backtrader.com/) to verify your results.
If your strategy fails, then it would most probably fail in other environments.

This is very much **alpha**

# Quickstart

```python
import pandas as pd
from datasource import DataSource
```
