import streamlit as st
import pandas as pd
from fastbt.rapid import backtest
from fastbt.datasource import DataSource


@st.cache
def load_data(x, y):
    tmp = x[x.symbol.isin(y)]
    return tmp


@st.cache
def transform(data):
    """
    Return transform data
    """
    ds = DataSource(data)
    ds.add_pct_change(col_name='ret', lag=1)
    ds.add_formula('(open/prevclose)-1', col_name='pret')
    return ds.data


@st.cache
def backtesting(data, **kwargs):
    results = backtest(data=data, **kwargs)
    return results


data_uploader = st.text_input(label='Enter the entire path of your file')
universe_uploader = st.file_uploader(label='Load your universe Excel file')
st.write(data_uploader)
st.write(universe_uploader)
universes = []
symbols = None
xls = None
data = None


if universe_uploader:
    xls = pd.ExcelFile(universe_uploader)
    universes = xls.sheet_names

universe_select = st.selectbox(label='Select your universe', options=universes)

if universe_select:
    st.write(universe_select)
    symbols = xls.parse(sheet_name=universe_select, header=None).values.ravel()
    symbols = list(symbols)
    if st.checkbox('Show symbols'):
        st.write(symbols)


order = st.radio('BUY or SELL', options=['B', 'S'])
price = st.text_input('Enter price formula', value='open')

stop_loss = st.number_input(label='stop loss', min_value=0.5, max_value=5.0, value=2.0, step=.5)

sort_by = st.selectbox('Select a metric to rank', ['pret', 'ret'])
sort_mode = st.radio('This is to select the bottom or top stocks', [True, False])

if data_uploader:
    data = pd.read_hdf(data_uploader)
    df2 = load_data(data, symbols)
    df2 = transform(df2)
    if st.checkbox('Run Backtest'):
        result = backtesting(data=df2, order=order, price=price, stop_loss=stop_loss, sort_by=sort_by, sort_mode=sort_mode)
