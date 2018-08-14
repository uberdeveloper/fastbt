# Basic assumption

**fastbt** is based on the following assumptions on entry and exit

1. You enter into a position at the start of the day
2. You exit your position either at the end of the day or by a stop loss
3. You take care of capital requirements

So your entry price is the price at which you want to buy a security and the exit price is either the stop loss price or the close price. Ideally, your entry price should be a limit order so that you are guaranteed execution at the specific price. If you prefer a market order, they you can model it as slippage.

# How prices are resolved?

**fastbt** resolves prices based on open, high, low, close, buy and sell prices for a security for that day.
So, you ideally place a **buy and sell order for the security with one of them being a stop loss.**

The orders are considered executed at the given price if the minimum of the buy and sell price is greater than the low price and the maximum of the buy and sell price is less than the high price of the security for the given period.

The order matching is done in the following way

- If both the BUY and SELL price are within the low-high range then the given BUY and SELL prices are taken
- If either BUY or SELL price is within the low-high range, then the other price is taken as the CLOSE price
- If both of them are not within the low-high range, then the order is considered as not executed

# Illustration

Let's illustrate the example with a security. Let's say we placed an order to buy the security at 1025 and place a stop loss at 1000.

### Case 1

---

| open | high | low | close | buy  | sell |
| ---- | ---- | --- | ----- | ---- | ---- |
| 1022 | 1030 | 994 | 1011  | 1025 | 1000 |

Here, the buy and sell price are within the low-high range.

- Low High range = 994 to 1030
- Sell Buy range = 1000 to 1025

So, both the orders would be executed at the given price

> BUY at 1025

> SELL at 1000

### Case 2.1

---

| open | high | low  | close | buy  | sell |
| ---- | ---- | ---- | ----- | ---- | ---- |
| 1022 | 1045 | 1016 | 1032  | 1025 | 1000 |

- Low High range = 1016 to 1045
- Sell buy range = 1000 to 1025

Here the BUY order would be executed at the given price.
Since the price of the SELL order is less than the lower price, the SELL price would be the close pirce 1032

> BUY at 1025

> SELL at 1032

### Case 2.2

| open | high | low | close | buy  | sell |
| ---- | ---- | --- | ----- | ---- | ---- |
| 1022 | 1022 | 950 | 1012  | 1025 | 1000 |

- Low High range = 950 to 1022
- Sell buy range = 1000 to 1025

Same as the above with BUY being executed at close price

> SELL at 1000

> BUY at 1012

### Case 3

---

| open | high | low  | close | buy  | sell |
| ---- | ---- | ---- | ----- | ---- | ---- |
| 1022 | 1023 | 1012 | 1022  | 1025 | 1000 |

- Low High range = 1012 to 1023
- Sell buy range = 1000 to 1025

No orders would be executed since both the buy and sell price are not within the low high range

## Why this approach?

This approach makes backtesting easier especially for short term trades.

Let's take the following example of a security price

| open | high | low | close |
| ---- | ---- | --- | ----- |
| 1000 | 1031 | 967 | 1018  |

So, if a place a BUY order at 1012 and a corresponding SELL order at 1020, there is a possibility that the security might have touched the low price before rebounding back. So this would severly impact my capital if I am trading on leverage. I can place a corresponding stop loss order but the positions are not safely hedged since I would be having 2 sell orders for 1 buy order which I need to cancel if one of them gets hit. So I prefer this approach.

> At present, this approach is tailored to day trading only but you can extend it to any frequency.

### Pros

- Easy to understand and simple to test
- No need for real time data. You can just use historical end of day data which is open source
- Predictable order executions in backtest
- Better comparison of backtest versus real performance
- Vectorized functions and parallel implementation

### Cons

- Too much opinionated
- Capital requirements not checked at each time frame
- No way to model relationsip among securities explicitly
- And a lot of goodies a full fledged backtesting framework provides

Some of the above cons can be overcome by extending the framework such as relaxing the assumptions or modeling it in a different manner
