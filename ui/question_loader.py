import json
from pathlib import Path

import streamlit as st


@st.cache_data
def load_questions():
    questions = []

    questions_folder = Path("data/questions")

    for file in sorted(questions_folder.glob("q_*.json")):
        with open(file, "r", encoding="utf-8") as f:
            questions.append(json.load(f))

    return questions
