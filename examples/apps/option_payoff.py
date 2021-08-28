import streamlit as st
import pandas as pd
from fastbt.options.order import OptionPayoff

if 'options' not in st.session_state:
    st.session_state.options = []

def update():
    kwargs = {
        'strike': int(st.session_state.strike),
        'opt_type': st.session_state.opt_type.upper()[0],
        'position': st.session_state.order.upper()[0],
        'premium': float(st.session_state.premium),
        'qty': int(st.session_state.quantity)*lot_size
    }
    st.session_state.options.append(kwargs)

cols = st.columns(2)
spot = cols[0].number_input('spot_price', value=15000,min_value=0, max_value=30000, step=100)
lot_size = cols[1].number_input('lot_size', min_value=1, value=1)

with st.form(key='opt_form'):
    columns = st.columns(5)
    columns[0].radio('Option', options=('put','call'), key='opt_type')
    columns[1].radio('Order type', options=('buy','sell'), key='order')
    columns[2].text_input('strike', key='strike', value=10000)
    columns[3].text_input('premium', key='premium', value=100)
    columns[4].text_input('quantity', key='quantity', value=1)
    submit = st.form_submit_button(label='Update', on_click=update)

payoff = OptionPayoff()
payoff.spot = spot
for opt in st.session_state.options:
    payoff.add(**opt)


st.write(pd.DataFrame(st.session_state.options))

collect = {}
for i in range(int(spot)-1000, int(spot)+1000):
    val = sum(payoff.calc(spot=i))
    collect[i] = val

s = pd.Series(collect)
s.name = 'pnl'
s.index.name = 'spot'
st.line_chart(s)
