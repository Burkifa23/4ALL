import os

import streamlit as st
from dotenv import load_dotenv


from ui.editor import render_editor
from ui.results import show_result
from sandbox.runner import run_submission, register_question

from evaluator.client import fetch_models
from evaluator.errors import EvaluatorError
from evaluator.generate import generate_question
from ui.question_loader import load_questions

# Reads OPENAI_API_KEY from .env so the sidebar key field comes pre-filled.
load_dotenv()

# EVALUATOR_MODE=stub swaps in the offline stand-in: identical signatures and
# return types, no Ollama, no 90-second waits. The test suite runs this way, and
# it is the demo fallback if the local model dies mid-presentation.
if os.environ.get("EVALUATOR_MODE") == "stub":
    from evaluator.stub import get_hint, evaluate_complexity
else:
    from evaluator.grading import evaluate_complexity
    from evaluator.hints import get_hint


from ui.history import initialize_history, add_attempt
from ui.sidebar import (
    render_custom_practice,
    render_sidebar,
    show_history,
    show_recommendation,
)
from recommender import assemble_features, recommend_next

st.set_page_config(page_title="Adaptive Assessor", layout="wide")


st.title("Adaptive AI Coding Assessment Platform")
initialize_history()

questions = load_questions()
questions_by_id = {q["question_id"]: q for q in questions}

# Model-written questions exist only for this session, and Streamlit rebuilds
# every local variable on each rerun — so they have to be re-merged and
# re-registered here, or the question the student is looking at vanishes the
# moment they press a button.
st.session_state.setdefault("generated", {})

for record in st.session_state.generated.values():
    register_question(record)

    questions_by_id[record["question_id"]] = record

# Navigation is by question_id, not list position — the recommender returns an
# id, and question order in the folder means nothing to it.
if "current_question_id" not in st.session_state:
    st.session_state.current_question_id = questions[0]["question_id"]

    st.session_state.served = [questions[0]["question_id"]]

    # Where the student is on the difficulty ladder. Only ever a real question
    # from data/questions/ — see the routing note further down.
    st.session_state.anchor_question_id = questions[0]["question_id"]

question = questions_by_id[st.session_state.current_question_id]

# Sidebar
#
# Only the settings render here. The recommendation and the history describe
# state the submit handler below is about to change, and Streamlit runs the
# script top to bottom — drawing them now would show the previous submission's
# decision while the Next button acted on the current one.

render_sidebar()

# Custom practice
#
# generate_question() only returns a question whose test cases its own
# reference solution passes — it runs them through the real sandbox before
# handing anything back. A model that invents a plausible problem and gets one
# expected value wrong is the failure mode here, and it is invisible on the
# page, so it has to be caught before the student ever sees the question.

request = render_custom_practice()

if request:
    try:
        with st.spinner(f"Writing a {request['topic']} question..."):
            record = generate_question(
                topic=request["topic"],
                difficulty=request["difficulty"],
                byom_config=st.session_state["byom_config"],
                model=request["model"],
            )

        st.session_state.generated[record["question_id"]] = record

        register_question(record)

        # The ladder position stays on the last real question. A generated
        # detour is practice, not progress through the question bank.
        st.session_state.current_question_id = record["question_id"]

        st.session_state.served.append(record["question_id"])

        for key in ("sandbox_result", "hint", "evaluation", "recommendation"):
            st.session_state.pop(key, None)

        st.rerun()

    except EvaluatorError as exc:
        st.error(exc.user_message)

        if exc.detail:
            with st.expander("Technical details"):
                st.code(exc.detail, language="text")

                st.caption(
                    f"Generator model {request['model']} - "
                    f"server {st.session_state['byom_config'].get('base_url')}"
                )

# Editor

code, submitted = render_editor(question)


# Submit button

if submitted:
    with st.spinner("Running test cases..."):
        sandbox_result = run_submission(code, question["question_id"])

    st.session_state["sandbox_result"] = sandbox_result

    # What ui/results.py attaches to a broken-test report. A report without the
    # code is unactionable: the whole question is whether the test is wrong or
    # the submission is.
    st.session_state["last_code"] = code

    st.session_state.pop("reported", None)

    byom_config = st.session_state["byom_config"]

    model_name = byom_config.get("model", "the model")

    evaluation = None

    # Grade a pass and nothing else. SandboxResult.status has five values, and
    # anything that isn't "passed" is code that did not work — grading it would
    # feed the recommender an efficiency score for code that never ran.
    #
    # An LLM failure must never abort the submission: the attempt is still
    # recorded (unscored) and still routed, and the recommender already falls
    # back to cold-start values for a missing score.
    try:
        if sandbox_result.status == "passed":
            with st.spinner(f"Asking {model_name} to review your solution..."):
                evaluation = evaluate_complexity(code, question, byom_config)

            st.session_state["evaluation"] = evaluation

        elif sandbox_result.failed_case_summary:
            # runner.py sets this on exactly the statuses worth hinting about
            # (failed / error / timeout) and leaves it None for "blocked" — a
            # security-blocked submission must not get coaching.
            with st.spinner(f"Asking {model_name} for a hint..."):
                st.session_state["hint"] = get_hint(
                    code, question, sandbox_result.failed_case_summary, byom_config
                )

    except EvaluatorError as exc:
        # errors.py already phrases these for students; never show a traceback.
        st.error(exc.user_message)

        # A wrong model name is the commonest BYOM mistake, and the endpoint
        # knows the right answer — so show it rather than making the user go
        # hunting through a provider's docs.
        available, _ = fetch_models(byom_config)

        if available and byom_config.get("model") not in available:
            st.warning(
                f"**{byom_config.get('model')}** is not one of the "
                f"{len(available)} models this endpoint offers. Pick one from "
                "the sidebar's Model list:\n\n"
                + "\n".join(f"- `{m}`" for m in available[:25])
                + ("\n- ..." if len(available) > 25 else "")
            )

        # Whoever is wiring up a model needs the technical cause — but a
        # student mid-assessment does not, so it stays collapsed.
        if exc.detail:
            with st.expander("Technical details"):
                st.code(exc.detail, language="text")

                st.caption(
                    f"Provider {byom_config.get('provider')} - "
                    f"model {byom_config.get('model')} - "
                    f"server {byom_config.get('base_url') or 'provider default'}"
                )

                st.caption("Setup help: docs/local_model_setup.md")

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

    # Route from the anchor, never from a generated question.
    #
    # The attempt itself is already in history above, so a custom-practice
    # detour still moves user_pass_rate and last_attempt_passed — the student's
    # work counts. What it must not do is set the difficulty and topic the next
    # decision is made from: a model-written "Hard" question is an unverified
    # difficulty label, and recommender.engine.pick_question only ever returns
    # ids from data/questions/, so routing off a generated question would ask
    # the model to level up from a rung that isn't on the ladder.
    anchor = questions_by_id[st.session_state.anchor_question_id]

    vector = assemble_features(st.session_state.history, anchor)

    st.session_state["recommendation"] = recommend_next(
        vector, exclude=st.session_state.served
    )

# Sidebar sections that describe post-submission state

show_recommendation()

show_history()

# Results

show_result()


recommendation = st.session_state.get("recommendation")

# A reinforce after a failure points back at the anchor — the student gets
# another go at it rather than being moved along. Compared against the anchor
# rather than the current question so that a custom-practice detour ending in
# "reinforce" reads as the return trip it is; on a normal question the anchor
# IS the current question, so this is the same test as before.
retrying = recommendation is not None and (
    recommendation.next_question_id == st.session_state.anchor_question_id
)

label = "Try Again" if retrying else "Next Question"

if st.button(label, key="next_question_btn", disabled=recommendation is None):
    st.session_state.current_question_id = recommendation.next_question_id

    # Always a question from data/questions/ — pick_question builds its index by
    # globbing that folder, so this is where the ladder position is restored
    # after a detour.
    st.session_state.anchor_question_id = recommendation.next_question_id

    if not retrying:
        st.session_state.served.append(recommendation.next_question_id)

    # These all describe the attempt being left behind.
    for key in ("sandbox_result", "hint", "evaluation", "recommendation"):
        st.session_state.pop(key, None)

    st.rerun()

if recommendation is None:
    st.caption("Submit a solution — the recommender picks the next question.")
