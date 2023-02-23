import pandas as pd
from typing import List, Tuple


class OptionsBacktest:
    """
    Backtesting a options strategy
    """

    def __init__(self, data: pd.DataFrame, start="9:30", end="15:15", tradebook=None):
        """
        options
            options data
        """
        self.data = data.copy()
        self.data["timestamp"] = self.data.timestamp + pd.Timedelta(seconds=1)
        self.start = start
        self.end = end
        if tradebook:
            print(tradebook)
            self.tradebook = tradebook
        else:
            self.tradebook = lambda x: x

    def generate_options_table(
        self, contracts: List[Tuple[str, str, int]]
    ) -> pd.DataFrame:
        """
        Given a list of contracts, generate the options table
        contracts
            list of 3-tuples in the form ('BUY', 'CALL', 0)
        """
        prices = (
            self.data.set_index("timestamp").between_time(self.start, self.start).spot
        )
        option_strikes = []
        for k, v in prices.items():
            strike = (int(v / 100) * 100) + 100

            def opt_type(x):
                return "CE" if x == "CALL" else "PE"

            def sign(x):
                return 1 if x == "BUY" else -1

            for ctx in contracts:
                side, opt, strk = ctx
                tup = (k.date(), strike + (strk * 100), opt_type(opt), sign(side))
                option_strikes.append(tup)
        columns = ["date", "strike", "opt", "side"]
        option_strikes = pd.DataFrame(option_strikes, columns=columns)
        option_strikes["date"] = pd.to_datetime(option_strikes.date.values)
        return option_strikes

    def get_result(self, data):
        res = pd.DataFrame.from_records(
            data,
            columns=["side", "entry_time", "entry_price", "exit_time", "exit_price"],
            index=data.index,
        )
        res["hour"] = res.exit_time.dt.hour
        res["year"] = res.exit_time.dt.year
        res["wkday"] = res.exit_time.dt.weekday
        res["profit"] = res.eval("(exit_price-entry_price)*side")
        return res.reset_index()

    def run(self, contracts):
        """
        Run the option with the given data
        """

        def f(x, stop=100):
            tb = self.tradebook(
                x.open.values,
                high=x.high.values,
                low=x.low.values,
                close=x.close.values,
                timestamp=x.timestamp.values,
                order=x.side.values[0],
                stop=stop,
            )
            return tb

        option_strikes = self.generate_options_table(contracts)
        run_data = (
            self.data.set_index("timestamp")
            .between_time(self.start, self.end)
            .reset_index()
        )
        run_data = run_data.merge(option_strikes, on=["date", "strike", "opt"])
        result = run_data.groupby(["date", "ticker"]).apply(f, stop=25)
        result = self.get_result(result)
        return result
