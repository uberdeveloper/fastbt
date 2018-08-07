from flask import Flask, render_template, request, jsonify
import sys
import os

sys.path.append('../')


class CustomFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='<[',
        block_end_string=']>',
        variable_start_string='[[',
        variable_end_string=']]',
        comment_start_string='<#',
        comment_end_string='#>',
    ))


app = CustomFlask(__name__)


@app.route('/')
def hello_world():
    context = {'name': 'Ram'}
    return render_template('index.html', **context)


@app.route('/test', methods=['GET', 'POST'])
def test():
    # Test function
    if request.method == 'POST':
        return str(request.form)

@app.route('/ds', methods=['GET', 'POST'])
def ds():
    if request.method == 'GET':
        return render_template('datastore.html')
    elif request.method == 'POST':
        print(request.form)
        return 'Hello Info Posted'



if __name__ == "__main__":
    app.run(debug=True)
