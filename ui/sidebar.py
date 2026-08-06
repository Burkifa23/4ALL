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

    retrying = recommendation.next_question_id == st.session_state.get(
        "current_question_id"
    )

    if recommendation.decision == "level_up":
        st.sidebar.success("Level up - next question is harder")
    elif retrying:
        st.sidebar.info("Reinforce - try this question again")
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
        # Keep these lines flush left. Markdown turns any line indented four or
        # more spaces into a code block, which is what made history rows render
        # inside stray fences.
        for i, item in enumerate(st.session_state.history, 1):
            scores = ""

            if item.get("efficiency_score") is not None:
                scores = (
                    f" - efficiency {item['efficiency_score']}"
                    f" / style {item['style_score']}"
                )

            st.sidebar.write(
                f"{i}. **{item['question_id']}** - {item['result']}{scores}"
            )
