"""
All simulations could be found here
"""
import pandas as pd
from typing import List, Callable


def walk_forward(
    data: pd.DataFrame,
    period: str,
    parameters: List[str],
    column: str,
    function: Callable,
    num: int = 1,
    ascending: bool = False,
) -> pd.DataFrame:
    """
    Do a simple walk forward test based on constant train
    and test period on a pandas dataframe
    data
        data as a pandas dataframe
    period
        period as a pandas frequency string
    factors
        list of parameters to be used in the test.
        These must be columns in the dataframe
    column
        The column to be used for running the test
    function
        The function to be run on the column
    num
        The number of results to be used for walk forward
    ascending
        Whether the top or bottom results to be taken
    """
    data["_period"] = data.index.to_period(period)
    columns = ["_period"] + parameters
    df = data.groupby(columns).agg({column: function}).reset_index()
    df2 = df.sort_values(by=column, ascending=ascending).groupby("_period").head(num)
    df2 = df2.set_index("_period").sort_index().shift(num)
    idx = df2.reset_index().drop(columns=column).dropna()
    return data.reset_index().merge(idx, on=columns)
