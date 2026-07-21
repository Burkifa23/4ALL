import streamlit as st

from ui.sidebar import render_sidebar
from ui.editor import render_editor
from ui.results import show_result
from sandbox.stub import run_submission

from evaluator.stub import get_hint, evaluate_complexity

st.set_page_config(page_title="Adaptive Assessor", layout="wide")


st.title("Adaptive AI Coding Assessment Platform")


# Initialize memory

if "result" not in st.session_state:
    st.session_state["result"] = "waiting"


# Fake question for now

question = {
    "title": "Two Sum",
    "difficulty": "Easy",
    "description": """
    Given an array of integers,
    return indices of two numbers
    that add up to a target.
    """,
    "starter_code": """
def two_sum(nums, target):
    # Write your solution here
    pass
""",
}


# Sidebar

render_sidebar()


# Editor

code, submitted = render_editor(question)


# Submit button

if submitted:
    sandbox_result = run_submission(code, "two_sum")

    st.session_state["sandbox_result"] = sandbox_result

    if sandbox_result.status == "failed":
        hint = get_hint(code, question, sandbox_result.failed_case_summary, "ollama")

        st.session_state["hint"] = hint

    else:
        evaluation = evaluate_complexity(code, question, "ollama")

        st.session_state["evaluation"] = evaluation
# Results

show_result()
