import streamlit as st


def initialize_history():

    if "history" not in st.session_state:
        st.session_state.history = []


def add_attempt(question_id, result, tests_passed, tests_total):

    attempt = {
        "question_id": question_id,
        "result": result,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
    }

    st.session_state.history.append(attempt)


def get_history():

    return st.session_state.history
