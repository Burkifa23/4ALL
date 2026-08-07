import os

import streamlit as st

from evaluator.client import fetch_models

# Starting points, not a whitelist. Every field a preset fills is editable, and
# "Custom" starts blank — so any OpenAI-compatible endpoint works, including
# ones nobody here has heard of. Adding a provider means adding a row of data,
# never a branch in the code.
#
# key_env is only where the API key is read from by default; the user can
# always type one instead.
PRESETS = {
    "Local (Ollama)": {
        "provider": "ollama",
        "base_url": "http://localhost:11434/v1",
        "model": "gemma2",
        "key_env": None,
    },
    "Local (LM Studio)": {
        "provider": "lmstudio",
        "base_url": "http://localhost:1234/v1",
        "model": "",
        "key_env": None,
    },
    "OpenAI": {
        "provider": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "key_env": "OPENAI_API_KEY",
    },
    "Groq": {
        "provider": "groq",
        "base_url": "https://api.groq.com/openai/v1",
        # Only a starting guess. Groq's /models needs a valid key, so the
        # dropdown stays empty until one is entered — pick from it once it
        # fills, since ids change as providers retire models.
        "model": "llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
    },
    "OpenRouter": {
        "provider": "openrouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "",
        "key_env": "OPENROUTER_API_KEY",
    },
    "Together": {
        "provider": "together",
        "base_url": "https://api.together.xyz/v1",
        "model": "",
        "key_env": "TOGETHER_API_KEY",
    },
    "Custom": {
        "provider": "custom",
        "base_url": "",
        "model": "",
        "key_env": "LLM_API_KEY",
    },
}

DEFAULT_LOCAL_URL = PRESETS["Local (Ollama)"]["base_url"]
OTHER = "Other (type it below)"


@st.cache_data(ttl=60, show_spinner=False)
def discover_models(base_url: str, api_key: str, _nonce: int = 0):
    """(models, reason) from the endpoint, cached so keystrokes don't hit the net.

    _nonce is bumped by the Refresh button to bypass the cache — useful after
    pasting a key, or after loading a model in LM Studio.
    """
    return fetch_models({"base_url": base_url, "api_key": api_key})


def _model_picker(base_url, api_key, default):
    """Pick from what the endpoint offers, but never trap the user in the list."""
    nonce = st.session_state.get("models_nonce", 0)

    available, reason = discover_models(base_url, api_key, nonce)

    if st.sidebar.button("Refresh model list", use_container_width=True):
        st.session_state["models_nonce"] = nonce + 1
        st.rerun()

    if not available:
        # Say why. A silent empty list leaves the user typing a model name
        # blind, which is how a typo becomes a 404 at submission time.
        st.sidebar.caption(f"Couldn't list models - {reason}. Type the name instead.")
        return st.sidebar.text_input("Model name", value=default)

    # Keep the preset's default selected when the endpoint offers it.
    index = available.index(default) if default in available else 0

    choice = st.sidebar.selectbox("Model", available + [OTHER], index=index)

    if choice == OTHER:
        return st.sidebar.text_input("Model name", value="")

    return choice


def render_sidebar():
    st.sidebar.title("Settings")

    name = st.sidebar.selectbox(
        "Provider",
        list(PRESETS),
        help="Any OpenAI-compatible API works. Pick the closest preset and "
        "edit the URL, or choose Custom.",
    )

    preset = PRESETS[name]

    # Every provider gets a URL. This is the fix for the old design, where only
    # the local branch had one and "cloud" silently meant api.openai.com — so a
    # Groq key was sent to OpenAI and rejected with a 401.
    base_url = st.sidebar.text_input(
        "Server URL",
        value=preset["base_url"],
        key=f"base_url_{name}",
        help="The OpenAI-compatible endpoint, usually ending in /v1.",
    )

    # Every provider gets a key field too. Local servers ignore it; hosted ones
    # need it. Pre-filled from the preset's environment variable so a student
    # with a .env never types it. Masked, kept in session state only, and never
    # written to disk or into a session transcript.
    api_key = st.sidebar.text_input(
        "API key",
        type="password",
        value=os.environ.get(preset["key_env"], "") if preset["key_env"] else "",
        key=f"api_key_{name}",
        help="Leave blank for local servers. Stored for this session only.",
    )

    model = _model_picker(base_url, api_key, preset["model"])

    if not base_url:
        st.sidebar.warning("Enter the server URL before submitting.")

    if not model:
        st.sidebar.warning("Enter a model name before submitting.")

    # The whole evaluator reads this one dict — see evaluator/client.py.
    st.session_state["byom_config"] = {
        "provider": preset["provider"],
        "model": model,
        "api_key": api_key or None,
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
