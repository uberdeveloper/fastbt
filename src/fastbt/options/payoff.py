"""
The options payoff module
"""
from typing import List, Dict, Optional, Union, Any
from collections import namedtuple
from enum import Enum
from pydantic import BaseModel, PrivateAttr, Field


class Opt(str, Enum):
    CALL = "c"
    PUT = "p"


class Side(Enum):
    BUY = 1
    SELL = -1


class OptionContract(BaseModel):
    strike: Union[int, float]
    option: Opt
    side: Side
    premium: float
    quantity: int


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
    """

    spot: float = 0.0
    _options: List[OptionContract] = PrivateAttr(default_factory=list)

    def _payoff(self, strike: float, option: str, position: str, **kwargs) -> float:
        """
        calculate the payoff for the option
        """
        comb = (option, position)
        spot = kwargs.get("spot", self.spot)
        if comb == ("C", "B"):
            return max(spot - strike, 0)
        elif comb == ("P", "B"):
            return max(strike - spot, 0)
        elif comb == ("C", "S"):
            return min(0, strike - spot)
        elif comb == ("P", "S"):
            return min(0, spot - strike)
        else:
            return 0

    def add(self, contract: OptionContract):
        """
        Add an option contract
        """
        self._options.append(contract)

    def add_contract(
        self,
        strike: float,
        opt_type: Opt = Opt.CALL,
        side: Side = Side.BUY,
        premium: float = 0.0,
        qty: int = 1,
    ) -> None:
        """
        Add an option
        strike
            strike price of the options
        opt_type
            option type - c for call and p for put
        position
            whether you are Buying or Selling the option
            B for buy and S for sell
        premium
            option premium
        qty
            quantity of options contract
        """
        contract = OptionContract(
            strike=strike, option=opt_type, side=side, premium=premium, quantity=qty
        )
        self._options.add(contract)

    @property
    def options(self) -> List[OptionContract]:
        """
        return the list of options
        """
        return self._options

    def clear(self) -> None:
        """
        Clear all options
        """
        self._options = []

    def calc(self, spot: Optional[float] = None) -> Union[List, None]:
        """
        Calculate the payoff
        """
        if not (spot):
            spot = self.spot
        payoffs = []
        for opt in self.options:
            profit = (self._payoff(**opt, spot=spot) + opt["premium"]) * abs(opt["qty"])
            payoffs.append(profit)
        return payoffs
