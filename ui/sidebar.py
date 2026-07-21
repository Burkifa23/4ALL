import streamlit as st


def render_sidebar():
    st.sidebar.title("Settings")

    provider = st.sidebar.radio(
        "Choose Model Provider", ["Local Ollama (Gemma)", "OpenAI Cloud"]
    )

    st.session_state["model_provider"] = provider

    st.sidebar.write(f"Selected: {provider}")


import streamlit as st


def show_history():

    st.sidebar.divider()

    st.sidebar.subheader("Session History")

    if "history" in st.session_state:
        for item in st.session_state.history:
            st.sidebar.write(
                f"""
                Question: {item["question_id"]}
                
                Result: {item["result"]}
                """
            )
