import streamlit as st


def render_editor(question):

    st.header(question["title"])

    # New schema from Person 1
    st.markdown(question["description_md"])

    # Convert difficulty number to readable text
    difficulty_map = {1: "Easy", 2: "Medium", 3: "Hard"}

    difficulty = difficulty_map.get(question["difficulty"], "Unknown")

    st.info(f"Difficulty: {difficulty}")

    code = st.text_area(
        "Write your Python solution:", height=300, value=question["starter_code"]
    )

    submit = st.button("Submit Code", key="submit_code_btn")

    return code, submit
