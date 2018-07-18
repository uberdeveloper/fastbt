from flask import Flask, render_template, request, jsonify
import sys
import os

sys.path.append('../')


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='%%',
        variable_end_string='%%',
        comment_start_string='<#',
        comment_end_string='#>',
    ))


app = CustomFlask(__name__)

from intraday import TradingSystem
import strategy as st

s_map = {x: getattr(st, x) for x in dir(st) if not(x.startswith('_'))}


@app.route('/')
def hello_world():
    context = {'name': 'Ram'}
    return render_template('index.html', **context)


@app.route('/test', methods=['GET', 'POST'])
def test():
    # Test function
    if request.method == 'POST':
        print(request.form)
        columns = request.form.get('columns')
        import json
        print('COLUMNS ', columns, type(columns), json.loads(columns))
        return columns


if __name__ == "__main__":
    app.run(debug=True)
