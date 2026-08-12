import json
from datetime import datetime
from pathlib import Path

import streamlit as st

REPORTS_PATH = Path("data/reports.jsonl")


def _show_hint():

    if "hint" in st.session_state:
        st.info(st.session_state["hint"].hint_text)


def _log_report(question_id, generated, result):
    """Append one "this test looks wrong" report.

    The generative path has a hole no amount of validation closes: the model
    can write a problem whose solution and test cases agree with each other but
    not with the description it wrote. That is coherent, passes the sandbox
    self-check, and is still unsolvable as written. The student is the only one
    who can see it, so give them somewhere to say so.

    Never let a write failure end an assessment — same reasoning as
    ui/history.save_session.
    """
    try:
        REPORTS_PATH.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "reported_at": datetime.now().isoformat(timespec="seconds"),
            "session_id": st.session_state.get("session_id"),
            "question_id": question_id,
            "generated": generated,
            "status": result.status,
            "tests_passed": result.tests_passed,
            "tests_total": result.tests_total,
            "failed_case_summary": result.failed_case_summary,
            "code": st.session_state.get("last_code", ""),
        }

        with REPORTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    except OSError:
        pass


def _report_broken_test(result):
    """Escape hatch for a question that cannot be solved as written."""

    question_id = st.session_state.get("current_question_id")

    generated = question_id in st.session_state.get("generated", {})

    if st.button("🚩 Report broken test", key="report_broken_test_btn"):
        _log_report(question_id, generated, result)

        st.session_state["reported"] = question_id

    if st.session_state.get("reported") != question_id:
        return

    st.caption(f"Logged to {REPORTS_PATH} — thanks.")

    # Only offered for generated questions: a question from data/questions/ has
    # a verified reference solution behind it, so the right move there is to
    # keep trying, not to skip.
    if generated and st.button("Discard it and go back to the track", key="discard_btn"):
        st.session_state.current_question_id = st.session_state.anchor_question_id

        for key in ("sandbox_result", "hint", "evaluation", "recommendation", "reported"):
            st.session_state.pop(key, None)

        st.rerun()


def show_result():
    """Render the outcome of the last submission.

    Every SandboxResult.status gets a branch. Leaving one out means the student
    submits and sees nothing at all, which is how a scoring bug went unnoticed
    for a whole session.
    """

    if "sandbox_result" not in st.session_state:
        st.info("Waiting for submission...")

        return

    result = st.session_state["sandbox_result"]

    if result.status == "passed":
        st.success(f"Passed {result.tests_passed}/{result.tests_total}")

        if "evaluation" in st.session_state:
            evaluation = st.session_state["evaluation"]

            st.code(evaluation.big_o_time, language="text")

            # Both scores are shown: the recommender routes on efficiency AND
            # style, so grading a student on a dimension they never see would
            # make the adaptive decisions unexplainable.
            left, right = st.columns(2)

            left.metric("Efficiency", f"{evaluation.efficiency_score}/5")

            right.metric("Style", f"{evaluation.style_score}/5")

            if evaluation.raw_feedback:
                with st.expander("Model feedback"):
                    st.write(evaluation.raw_feedback)

    elif result.status == "failed":
        st.error(f"Failed {result.tests_passed}/{result.tests_total}")

        st.write(result.failed_case_summary)

        _show_hint()

        _report_broken_test(result)

    elif result.status == "error":
        st.error("Your code could not run")

        st.write(result.failed_case_summary)

        _show_hint()

        _report_broken_test(result)

    elif result.status == "timeout":
        st.warning("Your code took too long and was stopped")

        st.write(result.failed_case_summary)

        _show_hint()

        _report_broken_test(result)

    elif result.status == "blocked":
        st.error("Blocked for security reasons - this code was never run")

        st.write(result.security_alert)
