import streamlit as st


def render_sidebar():
    st.sidebar.title("Settings")

    provider = st.sidebar.radio(
        "Choose Model Provider", ["Local Ollama (Gemma)", "OpenAI Cloud"]
    )

    st.session_state["model_provider"] = provider

    st.sidebar.write(f"Selected: {provider}")
