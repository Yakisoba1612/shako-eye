import streamlit as st

def apply_custom_css():
    st.markdown("""
        <style>
        /*ボタン類*/
        button[kind="primary"],
        button[kind="secondary"],
        button[data-testid^="baseButton"],
        [data-testid^="stBaseButton"],
        [data-testid="stElementToolbarButtonContainer"],
        [data-testid="stMainMenuButton"],
        
        /*入力フォーム*/
        [data-testid="stNumberInputContainer"],
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        div[data-baseweb="base-input"],
        
        /*通知画面*/
        div[data-testid="stAlert"],
        div[role="alert"],
        
        /*折りたたみ・ポップアップ*/
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        div[data-baseweb="popover"] > div
        {
            border-radius: 0px !important;
        }
        </style>
    """, unsafe_allow_html=True)