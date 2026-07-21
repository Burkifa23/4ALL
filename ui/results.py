import streamlit as st


def show_result():

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

        if "hint" in st.session_state:
            st.info(st.session_state["hint"].hint_text)
