import streamlit as st


from ui.editor import render_editor
from ui.results import show_result
from sandbox.stub import run_submission

from evaluator.stub import get_hint, evaluate_complexity
from ui.question_loader import load_questions


from ui.history import initialize_history, add_attempt
from ui.sidebar import render_sidebar, show_history, show_recommendation
from recommender import assemble_features, recommend_next

st.set_page_config(page_title="Adaptive Assessor", layout="wide")


st.title("Adaptive AI Coding Assessment Platform")
initialize_history()

questions = load_questions()
questions_by_id = {q["question_id"]: q for q in questions}

# Navigation is by question_id, not list position — the recommender returns an
# id, and question order in the folder means nothing to it.
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = questions[0]["question_id"]

    st.session_state.served = [questions[0]["question_id"]]

question = questions_by_id[st.session_state.current_question_id]

# Sidebar

render_sidebar()

show_recommendation()

show_history()

# Editor

code, submitted = render_editor(question)


# Submit button

if submitted:
    sandbox_result = run_submission(code, question["question_id"])

    st.session_state["sandbox_result"] = sandbox_result

    provider = st.session_state.get("model_provider", "ollama")

    evaluation = None

    if sandbox_result.status == "failed":
        st.session_state["hint"] = get_hint(
            code, question, sandbox_result.failed_case_summary, provider
        )

    else:
        evaluation = evaluate_complexity(code, question, provider)

        st.session_state["evaluation"] = evaluation

    # Grade first, then record: the attempt's scores are part of the history
    # row the recommender reads. And record before assembling features —
    # recommender/features.py defines every feature as including the attempt
    # just judged.
    add_attempt(
        question_id=question["question_id"],
        result=sandbox_result.status,
        tests_passed=sandbox_result.tests_passed,
        tests_total=sandbox_result.tests_total,
        evaluation=evaluation,
    )

    vector = assemble_features(st.session_state.history, question)

    st.session_state["recommendation"] = recommend_next(
        vector, exclude=st.session_state.served
    )

# Results

show_result()


recommendation = st.session_state.get("recommendation")

if st.button("Next Question", key="next_question_btn", disabled=recommendation is None):
    st.session_state.current_question_id = recommendation.next_question_id

    st.session_state.served.append(recommendation.next_question_id)

    # These all describe the question being left behind.
    for key in ("sandbox_result", "hint", "evaluation", "recommendation"):
        st.session_state.pop(key, None)

    st.rerun()

if recommendation is None:
    st.caption("Submit a solution — the recommender picks the next question.")
