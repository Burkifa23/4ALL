import os

import streamlit as st

# Label shown to the user -> the value contracts.types expects. client.py raises
# ValueError on anything else, so the contract value is what must be stored.
PROVIDERS = {
    "Local Ollama (Gemma)": "ollama",
    "OpenAI Cloud": "openai",
}


def render_sidebar():
    st.sidebar.title("Settings")

    label = st.sidebar.radio("Choose Model Provider", list(PROVIDERS))

    st.session_state["model_provider"] = PROVIDERS[label]

    st.sidebar.write(f"Selected: {label}")

    st.sidebar.divider()

    st.sidebar.subheader("Question Routing")

    # A/B switch for the demo: the trained classifier vs. the if/else baseline.
    # recommender.engine reads this environment variable on every call.
    use_baseline = st.sidebar.checkbox(
        "Use rules baseline (no ML)",
        value=False,
        help="Routes with the hand-written if/else gate instead of the "
        "trained decision tree.",
    )

    os.environ["RECOMMENDER_MODE"] = "baseline" if use_baseline else ""


def show_recommendation():
    """Make the adaptive decision visible — otherwise routing looks like magic."""

    recommendation = st.session_state.get("recommendation")

    if recommendation is None:
        return

    st.sidebar.divider()

    st.sidebar.subheader("Recommender")

    if recommendation.decision == "level_up":
        st.sidebar.success("Level up - next question is harder")
    else:
        st.sidebar.info("Reinforce - staying at this difficulty")

    st.sidebar.caption(
        f"confidence {recommendation.confidence:.0%} - "
        f"next: {recommendation.next_question_id}"
    )


def show_history():

    st.sidebar.divider()

    st.sidebar.subheader("Session History")

    if "history" in st.session_state:
        for item in st.session_state.history:
            scores = ""

            if item.get("efficiency_score") is not None:
                scores = (
                    f"\n\nEfficiency: {item['efficiency_score']} / "
                    f"Style: {item['style_score']}"
                )

            st.sidebar.write(
                f"""
                Question: {item["question_id"]}

                Result: {item["result"]}{scores}
                """
            )
