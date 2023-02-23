from typing import Tuple
import pendulum


def generic_parser(name: str) -> Tuple[str, float, pendulum.Date, str]:
    """
    A simple generic options parser
    """
    split = name.split("|")
    split[1] = float(split[1])
    date = split[2]
    print(date[:4], date[5:7], date[8:])
    split[2] = pendulum.date(
        year=int(date[:4]), month=int(date[5:7]), day=int(date[8:])
    )
    print(split[2])
    return tuple(split)
