import streamlit as st
import pandas as pd


def unpack_file(contents):
    xls = pd.ExcelFile(contents)
    return xls.sheet_names


uploader = st.file_uploader(label='Upload a file')

df2 = unpack_file(uploader)
choices = st.selectbox('Select an universe', options=df2)
st.write(choices)
