import json
import streamlit as st


@st.cache_data
def load_questions():

    with open("data/questions.json", "r") as file:
        return json.load(file)
