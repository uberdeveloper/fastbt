"""
Simple functional backtesting framework
based on end of day data

Assumptions
    1. Trades are done on an intraday basis
    2. Orders are placed at the beginning of the day
    3. Orders are closed when stop loss is hit or at the end of the day
    4. No target or pre-closing of orders
    5. All orders are placed/closed at the same time
"""

import pandas as pd
from datasource import DataSource

def tick(price, tick_size=0.05):
    """
    Rounds a given price to the requested tick
    """
    return round(price / tick_size)*tick_size

def isPrice(price, high, low):
    """
    Check whether the price is within the bound
    """
    return (price >= low) and (price <= high)

def fetch_data(universe, start, end, connection, tablename,
                where_clause = None):
    """
    Fetch data from SQL database
    where_clause
    additional where clauses as a list
    TO DO: Should adjust for date and time
    """
    q = []
    select = "SELECT * from {tablename} where ".format(tablename=tablename)
    if universe != 'all':
        q.append("symbol in {universe}")
    q.append("timestamp >= '{start}'")
    q.append("timestamp <= '{end}'")
    if where_clause:
        [q.append(x)for x in where_clause]
    order_by = ' ORDER BY timestamp'
    query = ' AND '.join(q).format(universe=tuple(universe), 
        start=start, end=end)
    query = select + query + order_by
    # This should be any column
    data = pd.read_sql_query(query, connection, parse_dates=['timestamp'])
    # Delete index column if any
    del data['index']
    return data

def prepare_data(data, columns):
    ds = DataSource(data, sort=False)
    return ds.batch_process(columns)

def apply_prices(data, conditions, price, stop_loss, order):
    """
    Filter conditions and apply prices
    data
        datasource object
    conditions
        list of conditions as string
    price
        price at which order is to be booked
        as a formula string
    stop_loss
        stop loss as percentage from price
    order
        whether the order is Buy or Sell
        accepted values B or S
    """

    if order.upper() == 'B':
        multiplier = 1 - (stop_loss * 0.01)
    elif order.upper() == 'S':
        multiplier = 1 + (stop_loss * 0.01)
    else:
        raise ValueError('Order should be either B or S')

    # All conditions are forced to lower case AND ed    
    big_condition = '&'.join(['(' + c.lower() + ')' for c in conditions])
    # TO DO: Deal with Memory Error in case of lots of conditions
    # f shorthand for filtered
    f = data.query(big_condition).copy()
    f['price'] = f.eval(price).apply(tick)
    f['stop_loss'] = (f['price'] * multiplier).apply(tick)

    # Price map to determine whether buy or sell is the entry
    p_map = {
        'B': ('buy', 'sell'),
        'S': ('sell', 'buy')
    }

    col_price, col_sl = p_map.get(order)

    f.loc[:, col_price] = [isPrice(p,h,l) for p,h,l in zip(
        f.price, f.high, f.low)] * f['price']
    f.loc[:, col_sl] = [isPrice(p,h,l) for p,h,l in zip(
        f.stop_loss, f.high, f.low)] * f['stop_loss']
    f.loc[f.buy == 0, 'buy'] = f.loc[f.buy == 0, 'close']
    f.loc[f.sell == 0, 'sell'] = f.loc[f.sell == 0, 'close']
    return f

def run_strategy(data, capital, leverage, limit, 
    sort_by, sort_mode, commission=0, slippage=0):
    total_capital = capital * leverage
    grouped = data.groupby('timestamp')
    collect = []
    for name, group in grouped:
        temp = group.sort_values(by=sort_by, ascending=sort_mode).iloc[:limit]
        L = len(temp)
        # Test for zero len
        if L > 0:
            capital_per_stock = total_capital/L
            temp['qty'] = (capital_per_stock/temp['price']).round(0)
            collect.append(temp)
    df = pd.concat(collect)
    df['profit'] = df.eval('(sell-buy)*qty')
    df['commission'] = df.eval('(sell+buy)*qty') * commission * 0.01
    df['slippage'] = df.eval('(sell+buy)*qty') *  slippage * 0.01
    df['net_profit'] = df.eval('profit - commission - slippage')
    return df

def metrics(data, capital, benchmark=None):
    if benchmark is None:
        benchmark = 0.08
    data['cumCap'] = data['net_profit'].cumsum() + capital
    profit = data.profit.sum()
    commission = data.commission.sum()
    slippage = data.slippage.sum()
    net_profit = data.net_profit.sum()
    high = data.cumCap.max()
    low = data.cumCap.min()
    drawdown = low/capital
    returns = net_profit/capital
    ret = data.groupby('timestamp').agg({'profit': sum})/capital
    sharpe = ret.mean() / ret.std()
    return {
        'profit': profit,
        'commission': commission,
        'slippage': slippage,
        'net_profit': net_profit,
        'high': high,
        'low': low,
        'drawdown': drawdown,
        'returns': returns,
        'sharpe': sharpe
    }       

def backtest(start='2018-04-01', end='2018-06-30',
            capital=100000, leverage=1, commission=0,
            slippage=0, price='open', stop_loss=0, order='B',
            universe='all', limit=5, columns=None, conditions=None,
            sort_by=None, sort_mode=True,
            connection=None, tablename=None):

    # Check whether any data is available

    isNotEmpty = lambda x: True if len(data) > 0 else False

    data = fetch_data(universe=universe, start=start, end=end,
                     connection=connection, tablename=tablename)

    if isNotEmpty(data):
        data = prepare_data(data, columns) 
        final = apply_prices(data, conditions, price, stop_loss, order) 
    else:
        raise ValueError('No data fetched from database')

    if isNotEmpty(final):
        result = run_strategy(final, capital, leverage, limit, sort_by, sort_mode)
    else:
        raise ValueError('No data after filtering all conditions')

    return result

def parse_input(input_data):
    pass

def main():
    print('Hi')

if __name__ == "__main__":
    main()
