import streamlit as st


def render_editor(question):

    st.header(question["title"])

    st.write(question["description"])

    st.info(f"Difficulty: {question['difficulty']}")

    code = st.text_area(
        "Write your Python solution:", height=300, value=question["starter_code"]
    )

    submit = st.button("Submit Code", key="submit_code_btn")

    return code, submit
