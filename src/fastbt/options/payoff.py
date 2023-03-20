"""
The options payoff module
"""
from typing import List, Optional, Union
from enum import Enum
from pydantic import BaseModel, PrivateAttr, root_validator
import logging
from collections import Counter


class Opt(str, Enum):
    CALL = "c"
    PUT = "p"
    FUTURE = "f"
    HOLDING = "h"


class Side(Enum):
    BUY = 1
    SELL = -1


class Contract(BaseModel):
    """
    A basic contract
    Could also include futures and holdings
    strike
        strike price of the contract.
        For futures/holdings, enter the price at which the
        contract is entered into
    option
        type of option contract could be call,put,future or holding
    side
        buy or sell/ 1 for buy and -1 for sell
    premium
        premium in case of an option
    quantity
        quantity of the contract
    """

    strike: Union[int, float]
    option: Opt
    side: Side
    premium: float = 0.0
    quantity: int = 1

    @root_validator
    def premium_check(cls, values):
        # Premium mandatory for call and put options
        option = values.get("option")
        premium = values.get("premium")
        if option in (Opt.CALL, Opt.PUT):
            if premium == 0.0:
                raise ValueError(f"Premium mandatory for {option} option")
        return values

    def value(self, spot: float) -> float:
        """
        Calculate the value of this contract given the spot
        at expiry for a single quantity
        """
        if self.option == Opt.CALL:
            return max(spot - self.strike, 0)
        elif self.option == Opt.PUT:
            return max(self.strike - spot, 0)
        else:
            return spot - self.strike

    def net_value(self, spot: float) -> float:
        """
        Return the net value for this contract given the
        spot price at expiry
        """
        val = self.value(spot=spot)
        if self.option in (Opt.CALL, Opt.PUT):
            return (val - self.premium) * self.side.value * self.quantity
        else:
            return val * self.side.value * self.quantity


class OptionPayoff(BaseModel):
    """
    A simple class for calculating option payoffs
    given spot prices and options
    1) Add your options with the add method
    2) Provide a spot price
    3) Call calculate to get the payoff for this spot price
    Note
    -----
    This class only does a simple arithmetic for the option and
    doesn't include any calculations for volatility or duration.
    It's assumed that the option is exercised at expiry and it
    doesn't have any time value
    spot
        spot price of the instrument
    lot_size
        lot size of the instrument for futures and options contract
    """

    spot: float = 0.0
    lot_size: int = 1
    _options: List[Contract] = PrivateAttr(default_factory=list)

    @staticmethod
    def _parse(text: str) -> Optional[Contract]:
        """
        Parse the text into a valid option contracts
        returns None if no such contract could be found
        """
        for opt in ("c", "p", "h", "f"):
            opt_parsed: List[str] = text.split(opt)
            if len(opt_parsed) == 2:
                strike, tail = opt_parsed
                for side in ("b", "s"):
                    tail_parsed = tail.split(side)
                    if len(tail_parsed) == 2:
                        premium, quantity = tail_parsed
                        if not premium:
                            premium = 0.0
                        if not quantity:
                            quantity = 1
                        s = 1 if side == "b" else -1
                        return Contract(
                            strike=strike,
                            option=opt,
                            side=s,
                            premium=premium,
                            quantity=quantity,
                        )
                logging.warning("No valid buy or sell identifier found")
        logging.warning("No valid option contract found")

    def a(self, text: str) -> None:
        """
        shortcut to add contract in text format
        contract should be in format `{strike}{opt}{premium}{side}{quantity}`
        *6500c150s2* is parsed as SELL 6500 CALL 2 lots at 150 premium
        """
        contract = self._parse(text)
        if contract:
            self._options.append(contract)

    def add(self, contract: Contract) -> None:
        """
        Add an option contract
        """
        self._options.append(contract)

    def add_contract(
        self,
        strike: float,
        option: Opt = Opt.CALL,
        side: Side = Side.BUY,
        premium: float = 0.0,
        quantity: int = 1,
    ) -> None:
        """
        Add an option
        strike
            strike price of the options
        option
            option type - c for call and p for put
        side
            whether you are Buying or Selling the option
            B for buy and S for sell
        premium
            option premium
        quantity
            quantity of options contract
        """
        contract = Contract(
            strike=strike, option=option, side=side, premium=premium, quantity=quantity
        )
        self._options.append(contract)

    @property
    def options(self) -> List[Contract]:
        """
        return the list of options
        """
        return self._options

    @property
    def net_positions(self) -> Counter:
        """
        returns the net positions for each type of contract
        call,put,futures,holdings
        """
        positions: Counter = Counter()
        for contract in self.options:
            quantity = contract.quantity * contract.side.value * self.lot_size
            positions[contract.option] += quantity
        return positions

    @property
    def has_naked_positions(self) -> bool:
        """
        returns True if there is a naked position
        Note
        -----
        1) Positions are considered naked if there are outstanding sell contracts
        2) Only CALL and PUT options are considered for naked positions
        """
        positions = self.net_positions
        if positions[Opt.CALL] < 0:
            return True
        elif positions[Opt.PUT] < 0:
            return True
        else:
            return False

    @property
    def is_zero(self) -> bool:
        """
        returns True if the sum of individual call and put
        options are zero and the combination of futures and
        holdings is zero
        Note
        ----
        1) If `is_zero` is True, we may assume that all
        positions are hedged
        2) If a future is hedged against option, then `is_zero` would return False
        """
        positions = self.net_positions
        comb = positions[Opt.FUTURE] + positions[Opt.HOLDING]
        call = positions[Opt.CALL]
        put = positions[Opt.PUT]
        if (comb == 0) and (call == 0) and (put == 0):
            return True
        else:
            return False

    def clear(self) -> None:
        """
        Clear all options
        """
        self._options = []

    def payoff(self, spot: Optional[float] = None) -> float:
        """
        Calculate the payoff given the spot price
        """
        if not spot:
            spot = self.spot
        if len(self.options) == 0:
            logging.debug("No contracts added, nothing to calculate")
            return 0.0
        return sum(
            [contract.net_value(spot) * self.lot_size for contract in self.options]
        )

    def simulate(self, spot: Union[List[float], List[int]]) -> List[float]:
        """
        Simulate option payoff for different spot prices
        """
        return [self.payoff(spot=price) for price in spot]
