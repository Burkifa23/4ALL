import json
import os
import urllib.request

import streamlit as st

# Label shown to the user -> the value contracts.types expects. client.py raises
# ValueError on anything else, so the contract value is what must be stored.
# "ollama" really means "any OpenAI-compatible server", which is the whole
# point of BYOM — the label says so even though the contract value can't.
PROVIDERS = {
    "Local model (Ollama / LM Studio / any OpenAI-compatible server)": "ollama",
    "OpenAI Cloud": "openai",
}

DEFAULT_LOCAL_URL = "http://localhost:11434/v1"
OTHER = "Other (type it below)"


@st.cache_data(ttl=30, show_spinner=False)
def list_local_models(base_url: str):
    """Ask an Ollama server what it actually has installed.

    Returns [] for anything that isn't a reachable Ollama — LM Studio, vLLM and
    llama.cpp serve the OpenAI API but not /api/tags, and that is fine: the UI
    falls back to a free-text field so any model name still works.
    """
    root = base_url.rstrip("/").removesuffix("/v1")
    try:
        with urllib.request.urlopen(f"{root}/api/tags", timeout=2) as response:
            payload = json.load(response)
        return sorted(m["name"] for m in payload.get("models", []))
    except Exception:
        return []


def _local_model_picker(base_url):
    """Pick from what's installed, but never trap the user in the list."""
    installed = list_local_models(base_url)

    if not installed:
        st.sidebar.caption(
            "No model list from this server — type the name your server uses."
        )
        return st.sidebar.text_input("Model name", value="gemma2")

    choice = st.sidebar.selectbox("Model", installed + [OTHER])

    if choice == OTHER:
        return st.sidebar.text_input("Model name", value="")

    return choice


def render_sidebar():
    st.sidebar.title("Settings")

    label = st.sidebar.radio("Choose Model Provider", list(PROVIDERS))

    provider = PROVIDERS[label]

    base_url = None

    # Only the cloud provider needs a key. Pre-filled from OPENAI_API_KEY so a
    # student with a .env never types it; masked either way, and it lives in
    # session state only — never written to disk or into a session transcript.
    api_key = None

    if provider == "ollama":
        # Editable so the model can live anywhere: another port, LM Studio on
        # 1234, a lab machine on the LAN, or a teammate's box.
        base_url = st.sidebar.text_input(
            "Server URL",
            value=DEFAULT_LOCAL_URL,
            help="Any OpenAI-compatible endpoint. Ollama defaults to "
            "http://localhost:11434/v1; LM Studio uses http://localhost:1234/v1.",
        )

        model = _local_model_picker(base_url)

    else:
        model = st.sidebar.text_input("Model name", value="gpt-4o-mini")

        api_key = st.sidebar.text_input(
            "OpenAI API key",
            type="password",
            value=os.environ.get("OPENAI_API_KEY", ""),
            help="Stored for this browser session only.",
        )

        if not api_key:
            st.sidebar.warning("An API key is required for the cloud provider.")

    if not model:
        st.sidebar.warning("Enter a model name before submitting.")

    # The whole evaluator reads this one dict — see evaluator/client.py.
    st.session_state["byom_config"] = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
    }

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
