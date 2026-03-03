"""
Shared helpers for example strategies.
"""

from datetime import datetime, timedelta
from typing import List


def make_clock(start: str = "09:15:00", end: str = "15:20:00") -> List[str]:
    """Generate a 1-minute clock from start to end (inclusive)."""
    fmt = "%H:%M:%S"
    current = datetime.strptime(start, fmt)
    stop = datetime.strptime(end, fmt)
    clock = []
    while current <= stop:
        clock.append(current.strftime(fmt))
        current += timedelta(minutes=1)
    return clock
