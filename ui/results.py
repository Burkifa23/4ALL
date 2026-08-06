import streamlit as st


def _show_hint():

    if "hint" in st.session_state:
        st.info(st.session_state["hint"].hint_text)


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

            st.write("Big O:", evaluation.big_o_time)

            st.write("Efficiency:", evaluation.efficiency_score)

    elif result.status == "failed":
        st.error(f"Failed {result.tests_passed}/{result.tests_total}")

        st.write(result.failed_case_summary)

        _show_hint()

    elif result.status == "error":
        st.error("Your code could not run")

        st.write(result.failed_case_summary)

        _show_hint()

    elif result.status == "timeout":
        st.warning("Your code took too long and was stopped")

        st.write(result.failed_case_summary)

        _show_hint()

    elif result.status == "blocked":
        st.error("Blocked for security reasons - this code was never run")

        st.write(result.security_alert)
