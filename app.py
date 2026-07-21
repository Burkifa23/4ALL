import streamlit as st


from ui.editor import render_editor
from ui.results import show_result
from sandbox.stub import run_submission

from evaluator.stub import get_hint, evaluate_complexity
from ui.question_loader import load_questions


from ui.history import initialize_history, add_attempt
from ui.sidebar import render_sidebar, show_history

st.set_page_config(page_title="Adaptive Assessor", layout="wide")


st.title("Adaptive AI Coding Assessment Platform")
initialize_history()

# Initialize memory


# Fake question for now

questions = load_questions()

if "current_question" not in st.session_state:
    st.session_state.current_question = 0


question = questions[st.session_state.current_question]
# Sidebar

render_sidebar()

show_history()
# Editor

code, submitted = render_editor(question)


# Submit button

if submitted:
    sandbox_result = run_submission(code, question["id"])

    st.session_state["sandbox_result"] = sandbox_result
    add_attempt(
        question_id=question["id"],
        result=sandbox_result.status,
        tests_passed=sandbox_result.tests_passed,
        tests_total=sandbox_result.tests_total,
    )

    if sandbox_result.status == "failed":
        provider = st.session_state.get("model_provider", "ollama")
        hint = get_hint(code, question, sandbox_result.failed_case_summary, provider)

        st.session_state["hint"] = hint

    else:
        evaluation = evaluate_complexity(code, question, "ollama")

        st.session_state["evaluation"] = evaluation
# Results

show_result()


if st.button("Next Question", key="next_question_btn"):
    st.session_state.current_question += 1

    if st.session_state.current_question >= len(questions):
        st.session_state.current_question = 0

    st.rerun()
