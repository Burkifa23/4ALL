import streamlit as st


def initialize_history():

    if "history" not in st.session_state:
        st.session_state.history = []


def add_attempt(question_id, result, tests_passed, tests_total, evaluation=None):
    """Record one submission.

    evaluation: the LLMEvaluation for this attempt, when one was produced.
    Only passing submissions get graded, so failures carry no scores — the
    recommender expects exactly that and falls back to its cold-start values.
    These two fields are what feed the model's efficiency/style features, so
    dropping them here silently degrades every recommendation.
    """

    attempt = {
        "question_id": question_id,
        "result": result,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "efficiency_score": evaluation.efficiency_score if evaluation else None,
        "style_score": evaluation.style_score if evaluation else None,
    }

    st.session_state.history.append(attempt)


def get_history():

    return st.session_state.history
