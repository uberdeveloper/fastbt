import time
from fastbt.backtest.data import DuckDBParquetLoader


class DummyTrade:
    """Super simple trade class just to track conditions."""

    def __init__(
        self,
        strike: int,
        opt_type: str,
        direction: str,
        entry_price: float,
        entry_time: str,
    ):
        self.strike = strike
        self.opt_type = opt_type
        self.direction = direction  # 'SELL' or 'BUY'
        self.entry_price = entry_price
        self.entry_time = entry_time

    def current_loss(self, current_price: float) -> float:
        # If I sold, lower price is better. Net PnL = (Entry - Current)
        if self.direction == "SELL":
            return self.entry_price - current_price
        return current_price - self.entry_price

    def __repr__(self):
        return f"{self.direction} {self.strike}{self.opt_type} at {self.entry_price}"


class IntradayDummyEngine:
    """
    Tests our dict-based lazy fetch caching.
    """

    def __init__(self, data_path: str):
        self.loader = DuckDBParquetLoader(data_path)
        self.cache = {}
        self.open_positions = []
        self.logs = []

    def log(self, time_str: str, msg: str):
        self.logs.append(f"[{time_str}] {msg}")

    def run_day(self, date_str: str):
        """Runs an intraday time loop."""
        print(f"--- Starting run for {date_str} ---")

        # 1. Fetch Master Clock
        t0 = time.time()
        clock = self.loader.get_underlying_data(date_str)
        print(
            f"Loaded Master Clock: {len(clock)} ticks in {(time.time() - t0)*1000:.2f}ms"
        )

        # The main event loop
        for loop_time, spot_price in clock.items():

            # --- Condition Check Level (Cache Hit) ---
            # E.g. Stop Loss monitoring
            for trade in self.open_positions[:]:
                # We know for a absolute fact the option's dict is cached!
                cache_key = f"{trade.strike}_{trade.opt_type}"
                try:
                    current_leg_price = self.cache[cache_key][loop_time]["close"]
                except KeyError:
                    self.log(loop_time, f"No bar for {cache_key} (maybe illiquid min)")
                    continue

                pnl = trade.current_loss(current_leg_price)
                if pnl <= -20:  # Stop Loss Trigger
                    self.log(
                        loop_time,
                        f"EXIT {trade} at {current_leg_price}. PNL: {pnl:.2f}",
                    )
                    self.open_positions.remove(trade)
                    # For dummy sake, let's reverse direction immediately on stop out
                    self.enter_trade(
                        date_str, loop_time, spot_price, trade.opt_type, "BUY"
                    )

            # --- Entry Condition Level (Cache Miss / Lazy Fetch) ---
            if loop_time == "09:40:00":
                # Entry Strategy: Sell an ATM call
                self.log(loop_time, f"Signal generated (Spot: {spot_price})")
                self.enter_trade(date_str, loop_time, spot_price, "CE", "SELL")

        print("\n".join(self.logs))

    def enter_trade(
        self,
        date_str: str,
        time_str: str,
        spot_price: float,
        opt_type: str,
        direction: str,
    ):
        atm = DuckDBParquetLoader.get_atm_strike(spot_price, step=50)
        cache_key = f"{atm}_{opt_type}"

        # Only query if we haven't already!
        if cache_key not in self.cache:
            t1 = time.time()
            data = self.loader.get_instrument_data(date_str, atm, opt_type)
            self.cache[cache_key] = data
            self.log(
                time_str,
                f"LAZY FETCH: {cache_key} fetched {len(data)} bars to cache in {(time.time()-t1)*1000:.2f}ms",
            )

        # Execute the trade
        try:
            entry_price = self.cache[cache_key][time_str]["close"]
            trade = DummyTrade(atm, opt_type, direction, entry_price, time_str)
            self.open_positions.append(trade)
            self.log(time_str, f"ENTER: {trade}")
        except KeyError:
            self.log(
                time_str,
                f"FAILED TO ENTER: No price data for {cache_key} at {time_str}",
            )


if __name__ == "__main__":
    engine = IntradayDummyEngine("/home/pi/data/q1_2025.parquet")
    engine.run_day("2025-01-01")
