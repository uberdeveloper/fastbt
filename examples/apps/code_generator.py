import streamlit as st
import pandas as pd
import yaml
from fastbt.experimental import CodeGenerator


@st.cache
def load_data():
    pass


st.title('Code Generator')

cg = CodeGenerator(name='tradebook')

file_input = st.file_uploader('Upload a blocks file')

if file_input:
    dct = yaml.safe_load(file_input)
    for k, v in dct.items():
        cg.add_code_block(k, v)

    blocks = st.multiselect(label='Available blocks',
                            options=list(dct.keys()))
    st.write(blocks)
    cg.clear()
    for k, v in dct.items():
        cg.add_code_block(k, v)
    cg.add_text('class NewClass:')
    for b in blocks:
        cg.add_block(b, indent=True)
    code = cg.generate_code()
    code = '```python' + '\n' + code + '\n' + '```'
    st.markdown(code)
    st.text(code)
