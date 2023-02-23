"""
A plotting module for easy plotting of financial charts
"""
from bokeh.plotting import figure
from bokeh.models import ColumnDataSource
import pandas as pd
from math import pi


def candlestick_plot(data, title="Candlestick", interval="5min"):
    """
    return a bokeh candlestick plot
    data
        dataframe with open,high,low and close columns
    Note
    -----
    Prototype copied from the below link
    https://bokeh.pydata.org/en/latest/docs/gallery/candlestick.html
    """
    df = data.copy()
    df["date"] = pd.to_datetime(df["timestamp"])
    df["date"] = df["date"]
    df["color"] = ["green" if x > y else "red" for (x, y) in zip(df.close, df.open)]
    source = ColumnDataSource()
    source.data = source.from_df(df)
    spacing = int(interval[:-3]) * 0.3
    w = spacing * 60 * 1000  # half day in ms
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    p = figure(
        x_axis_type="datetime",
        tools=TOOLS,
        title=title,
        plot_width=720,
        tooltips=[
            ("date", "@date{%F %H:%M}"),
            ("open", "@open{0.00}"),
            ("high", "@high{0.00}"),
            ("low", "@low{0.00}"),
            ("close", "@close{0.00}"),
        ],
    )
    p.hover.formatters = {"@date": "datetime"}
    p.xaxis.major_label_orientation = pi / 4
    p.grid.grid_line_alpha = 0.3
    p.segment("date", "high", "date", "low", color="black", source=source)
    p.vbar(
        "date",
        w,
        "open",
        "close",
        fill_color="color",
        line_color="black",
        source=source,
    )
    return p
