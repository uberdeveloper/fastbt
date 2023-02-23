from flask import Flask, render_template, request
from fastbt.rapid import backtest
import pandas as pd


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(
        dict(
            block_start_string="<%",
            block_end_string="%>",
            variable_start_string="%%",
            variable_end_string="%%",
            comment_start_string="<#",
            comment_end_string="#>",
        )
    )


app = CustomFlask(__name__)


@app.route("/")
def hello_world():
    col_types = ["lag", "percent_change", "rolling", "formula", "indicator"]
    context = {"name": "Ram", "col_types": col_types}
    return render_template("backtest.html", **context)


@app.route("/backtest", methods=["POST"])
def run_backtest():
    if request.method == "POST":
        pass
        # return str(request.form)
    df = pd.read_csv(
        "/home/machine/Projects/finance/nifty50", parse_dates=["timestamp"]
    )
    import json

    columns = json.loads(request.form.get("columns"))
    conditions = json.loads(request.form.get("conditions"))
    print(columns)
    result = backtest(
        data=df, order="S", stop_loss=3, columns=columns, conditions=conditions
    )
    txt = str(result.columns)
    return str(result.net_profit.sum()) + "\n" + txt


@app.route("/ds", methods=["GET", "POST"])
def ds():
    controls = [
        {
            "input": True,
            "type": "file",
            "name": "directory",
            "placeholder": "Select a directory with a file",
        },
        {
            "input": True,
            "type": "text",
            "name": "engine",
            "placeholder": "sqlalchemy connection string or HDF5 filename",
        },
        {
            "input": True,
            "type": "text",
            "name": "tablename",
            "placeholder": "tablename in SQL or HDF",
        },
        {"select": True, "name": "mode", "choices": ["SQL", "HDF"]},
    ]
    context = {"controls": controls}
    if request.method == "GET":
        return render_template("datastore.html", **context)
    elif request.method == "POST":
        print(request.form)
        return str(request.form)


if __name__ == "__main__":
    app.run(debug=True)
