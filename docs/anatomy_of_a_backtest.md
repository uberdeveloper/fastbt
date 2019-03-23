# Introduction

Let's look at what the backtest exactly works under the hoods. These are the series of steps the backtest performs.

1.  All stocks from the given universe are selected from the data provided
2.  The columns are strictly added in the order in which they are created
3.  Conditions are applied in the given order to filter and narrow down stocks
4.  From the filtered list, the price and the stop loss for each stock is calculated
5.  Stocks are then sorted based on the given column and the top n stocks are picked.
6.  The quantity for each stock is determined by the trading capital and the number of stocks. **All stocks are equi-weighted.**
7.  Profit or loss for each day is then calculated based on OHLC data, price and stop loss.
8.  Commission and slippage is deducted from the above profit to get the net profit
9.  The above process is repeated for each day and the results are then accumulated

## Profit calculation

Profit is calculated by comparing price and stop loss with OHLC data. If price is within the high-low range it is assumed that the order would get placed. The following table shows how profit is calculated (range means the high-low range)

| price        | stop_loss    | profit (long/buy) | (profit (short/sell) |
| ------------ | ------------ | ----------------- | -------------------- |
| in range     | not in range | close-price       | price-close          |
| in range     | in range     | stop_loss-price   | price-stop_loss      |
| not in range | in range     | stop_loss-close   | close-stop_loss      |
| not in range | not in range | nothing           | nothing              |

See the rationale page for how this price is calculated.
