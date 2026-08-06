"""End-to-end checks that the app actually routes through the recommender.

Runs the real app.py headlessly with streamlit's AppTest — no browser.

    python tests/test_app_integration.py

These are the two behavioural acceptance tests for the adaptive path: ace an
easy question and the next one gets harder; fail repeatedly and it does not.
The sandbox stub passes any submission containing "print", so that string is
what "solved it" means here.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest  # noqa: E402

from recommender import engine  # noqa: E402

# data/predictions.jsonl is the Week 13 evaluation dataset — keep test runs out.
engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_apptest.jsonl"

PASSING_CODE = "print('solved')"
FAILING_CODE = "pass"


def _load_questions():
    import json

    return {
        q["question_id"]: q
        for q in (
            json.loads(p.read_text(encoding="utf-8"))
            for p in sorted(Path("data/questions").glob("q_*.json"))
        )
    }


def run_app():
    app = AppTest.from_file("app.py", default_timeout=30)
    app.run()
    assert not app.exception, app.exception
    return app


def submit(app, code):
    """Type into the editor and hit Submit, the way a student would."""
    app.text_area[0].set_value(code)
    app.button(key="submit_code_btn").click().run()
    assert not app.exception, app.exception
    return app


def test_app_starts_clean():
    app = run_app()
    assert app.session_state["current_question_id"] == "q_0001"
    assert app.session_state["served"] == ["q_0001"]
    # No recommendation before a submission, so advancing is blocked.
    assert "recommendation" not in app.session_state
    assert app.button(key="next_question_btn").disabled


def test_passing_submission_records_scores_and_recommends():
    app = submit(run_app(), PASSING_CODE)

    attempt = app.session_state["history"][-1]
    assert attempt["question_id"] == "q_0001"
    assert attempt["result"] == "passed"
    # The whole point of the history change: scores must reach the recommender.
    assert attempt["efficiency_score"] == 4
    assert attempt["style_score"] == 5

    rec = app.session_state["recommendation"]
    assert rec.decision in ("level_up", "reinforce")
    assert rec.next_question_id != "q_0001"
    assert not app.button(key="next_question_btn").disabled


def test_ace_an_easy_question_levels_up():
    """ACCEPTANCE: solve an Easy question first try -> next question is harder."""
    app = submit(run_app(), PASSING_CODE)

    rec = app.session_state["recommendation"]
    assert rec.decision == "level_up", rec

    questions = _load_questions()
    assert questions["q_0001"]["difficulty"] == 1
    assert questions[rec.next_question_id]["difficulty"] == 2, (
        f"expected a Medium question, got "
        f"{questions[rec.next_question_id]['difficulty']}"
    )


def test_repeated_failure_reinforces():
    """ACCEPTANCE: keep failing -> stay at the same difficulty."""
    app = run_app()
    for _ in range(3):
        submit(app, FAILING_CODE)

    rec = app.session_state["recommendation"]
    assert rec.decision == "reinforce", rec

    questions = _load_questions()
    assert questions[rec.next_question_id]["difficulty"] == 1, "should stay Easy"

    # Failures carry no LLM scores — only passing submissions get graded.
    assert all(a["efficiency_score"] is None for a in app.session_state["history"])


def test_advancing_clears_the_previous_question():
    app = submit(run_app(), PASSING_CODE)
    next_id = app.session_state["recommendation"].next_question_id

    app.button(key="next_question_btn").click().run()
    assert not app.exception, app.exception

    assert app.session_state["current_question_id"] == next_id
    assert next_id in app.session_state["served"]
    # Stale results from the previous question must not leak onto the new one.
    for key in ("sandbox_result", "hint", "evaluation", "recommendation"):
        assert key not in app.session_state, f"{key} leaked across questions"
    # History survives — it is the feature source.
    assert len(app.session_state["history"]) == 1


def test_never_reserves_a_served_question():
    app = run_app()
    for _ in range(4):
        submit(app, PASSING_CODE)
        app.button(key="next_question_btn").click().run()
        assert not app.exception, app.exception

    served = app.session_state["served"]
    assert len(served) == len(set(served)), f"repeat served: {served}"


def test_provider_is_the_contract_value():
    """client.py raises on anything but 'ollama'/'openai' — not the UI label."""
    app = run_app()
    assert app.session_state["model_provider"] in ("ollama", "openai")


def test_baseline_mode_switch():
    app = run_app()
    app.sidebar.checkbox[0].set_value(True).run()
    submit(app, PASSING_CODE)
    # The rules baseline reports full confidence by construction.
    assert app.session_state["recommendation"].confidence == 1.0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("\napp integration checks passed")
