"""End-to-end checks that the app routes through the recommender correctly.

Runs the real app.py headlessly with streamlit's AppTest, against the real
sandbox in sandbox/runner.py — no browser, no stubs for execution.

    python tests/test_app_integration.py

Code fixtures are derived from the question data rather than hardcoded, so they
stay valid whatever question the recommender serves:

    passing  reference_solution        -> status "passed"
    failing  returns None              -> status "failed"
    error    signature, no body        -> status "error"  (IndentationError)
    blocked  imports os                -> status "blocked"

Note that `starter_code` itself yields "failed", not "error": it ships with a
`pass` body, so it parses and runs and simply returns None for every case. The
"error" fixture reproduces what a student produces by deleting that body.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from streamlit.testing.v1 import AppTest  # noqa: E402

from recommender import engine  # noqa: E402

# data/predictions.jsonl is the Week 13 evaluation dataset — keep test runs out.
engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_apptest.jsonl"

QUESTIONS = {
    q["question_id"]: q
    for q in (
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(Path("data/questions").glob("q_*.json"))
    )
}


def passing_code(question_id):
    return QUESTIONS[question_id]["reference_solution"]


def failing_code(question_id):
    """Parses and runs, returns None for every case — the reported 'got None'."""
    method = QUESTIONS[question_id]["entry_point"].split(".")[-1]
    return f"class Solution:\n    def {method}(self, *args, **kwargs):\n        return None\n"


def error_code(question_id):
    """A signature with the body deleted — an IndentationError, so it never runs.

    This is what a student produces by clearing the starter body before typing
    a solution, and it is the exact shape that triggered the reported bug.
    """
    method = QUESTIONS[question_id]["entry_point"].split(".")[-1]
    return (
        "from typing import List\n"
        "\n"
        "class Solution:\n"
        f"    def {method}(self, nums: List[int]) -> int:\n"
        "        \n"
    )


def blocked_code(question_id):
    method = QUESTIONS[question_id]["entry_point"].split(".")[-1]
    return (
        "import os\n"
        "class Solution:\n"
        f"    def {method}(self, *args, **kwargs):\n"
        "        return os.getcwd()\n"
    )


def run_app():
    app = AppTest.from_file("app.py", default_timeout=120)
    app.run()
    assert not app.exception, app.exception
    return app


def current_id(app):
    return app.session_state["current_question_id"]


def submit(app, code_fn):
    """Type into the editor and hit Submit, the way a student would."""
    app.text_area[0].set_value(code_fn(current_id(app)))
    app.button(key="submit_code_btn").click().run()
    assert not app.exception, app.exception
    return app


def advance(app):
    """Click the next/retry button, whatever it is currently labelled."""
    app.button(key="next_question_btn").click().run()
    assert not app.exception, app.exception
    return app


def button_label(app):
    return app.button(key="next_question_btn").label


def difficulty_of(question_id):
    return QUESTIONS[question_id]["difficulty"]


def test_app_starts_clean():
    app = run_app()
    assert current_id(app) == "q_0001"
    assert app.session_state["served"] == ["q_0001"]
    assert "recommendation" not in app.session_state
    assert app.button(key="next_question_btn").disabled


def test_passing_submission_records_scores_and_recommends():
    app = submit(run_app(), passing_code)

    attempt = app.session_state["history"][-1]
    assert attempt["question_id"] == "q_0001"
    assert attempt["result"] == "passed", attempt
    # The whole point of the history change: scores must reach the recommender.
    assert attempt["efficiency_score"] == 4
    assert attempt["style_score"] == 5

    rec = app.session_state["recommendation"]
    assert rec.next_question_id != "q_0001"
    assert not app.button(key="next_question_btn").disabled


def test_ace_an_easy_question_levels_up():
    """ACCEPTANCE: solve an Easy question first try -> next question is harder."""
    app = submit(run_app(), passing_code)

    rec = app.session_state["recommendation"]
    assert rec.decision == "level_up", rec
    assert difficulty_of("q_0001") == 1
    assert difficulty_of(rec.next_question_id) == 2, rec


def test_repeated_failure_reinforces():
    """ACCEPTANCE: keep failing -> stay at the same difficulty."""
    app = run_app()
    for _ in range(3):
        submit(app, failing_code)

    rec = app.session_state["recommendation"]
    assert rec.decision == "reinforce", rec
    assert difficulty_of(rec.next_question_id) == 1, "should stay Easy"

    # Failures carry no LLM scores — only passing submissions get graded.
    assert all(a["efficiency_score"] is None for a in app.session_state["history"])


# --- the recommendation shown is the one acted on --------------------------


def test_sidebar_shows_the_decision_that_is_acted_on():
    """REGRESSION: the sidebar used to render before the submit handler ran.

    It showed the *previous* submission's decision while the button navigated
    with the current one — "Reinforce, next q_0002" on screen, Medium question
    served.
    """
    app = submit(run_app(), passing_code)
    shown = app.session_state["recommendation"]

    advance(app)

    assert current_id(app) == shown.next_question_id
    assert difficulty_of(current_id(app)) == (
        2 if shown.decision == "level_up" else 1
    ), (shown.decision, current_id(app))


def test_history_is_current_after_submitting():
    """The history the sidebar draws must include the attempt just judged."""
    app = submit(run_app(), failing_code)
    assert len(app.session_state["history"]) == 1

    submit(app, failing_code)
    assert len(app.session_state["history"]) == 2


# --- failing keeps you on the question -------------------------------------


def test_failure_retries_the_same_question():
    """A failed attempt re-serves the same question instead of moving on."""
    app = submit(run_app(), failing_code)

    rec = app.session_state["recommendation"]
    assert rec.decision == "reinforce"
    assert rec.next_question_id == "q_0001", rec
    assert button_label(app) == "Try Again", button_label(app)

    advance(app)
    assert current_id(app) == "q_0001", "should still be on the same question"
    # A retry is not a new question, so it must not be added to served.
    assert app.session_state["served"] == ["q_0001"]


def test_retry_limit_moves_to_a_new_question():
    """After RETRY_LIMIT failures, move to a different question, same difficulty."""
    from recommender.engine import RETRY_LIMIT

    app = run_app()
    for _ in range(RETRY_LIMIT - 1):
        submit(app, failing_code)
        assert app.session_state["recommendation"].next_question_id == "q_0001"
        advance(app)
        assert current_id(app) == "q_0001"

    submit(app, failing_code)
    rec = app.session_state["recommendation"]
    assert rec.next_question_id != "q_0001", rec
    assert difficulty_of(rec.next_question_id) == 1, "difficulty must hold"
    assert button_label(app) == "Next Question"

    advance(app)
    assert current_id(app) != "q_0001"


def test_passing_always_moves_on():
    app = submit(run_app(), passing_code)
    rec = app.session_state["recommendation"]
    assert rec.next_question_id != "q_0001"
    assert button_label(app) == "Next Question"


# --- regression: broken code must not be graded as good code ---------------


def test_error_submission_is_not_graded():
    """Code that doesn't parse must not receive a grade.

    The original bug: status "error" fell into app.py's else branch, got sent to
    evaluate_complexity, came back 4/5, and the recommender levelled the student
    up for code that never ran.
    """
    app = submit(run_app(), error_code)

    attempt = app.session_state["history"][-1]
    assert attempt["result"] == "error", attempt
    assert attempt["efficiency_score"] is None, "code that never ran was graded"
    assert attempt["style_score"] is None
    assert "evaluation" not in app.session_state

    rec = app.session_state["recommendation"]
    assert rec.decision == "reinforce", rec
    assert difficulty_of(rec.next_question_id) == 1, "errors must not raise difficulty"


def test_reported_escalation_does_not_happen():
    """The exact reported sequence: two failures, then starter code repeatedly.

    Previously escalated Easy -> Medium -> Hard on nothing but syntax errors.
    """
    app = run_app()
    submit(app, failing_code)
    submit(app, failing_code)
    assert app.session_state["recommendation"].decision == "reinforce"

    for _ in range(3):
        advance(app)
        submit(app, error_code)
        rec = app.session_state["recommendation"]
        assert rec.decision == "reinforce", (current_id(app), rec)
        assert difficulty_of(current_id(app)) == 1, "climbed difficulty on errors"

    assert all(a["efficiency_score"] is None for a in app.session_state["history"])


def test_blocked_submission_is_not_graded_and_gets_no_hint():
    app = submit(run_app(), blocked_code)

    attempt = app.session_state["history"][-1]
    assert attempt["result"] == "blocked", attempt
    assert attempt["efficiency_score"] is None
    assert "evaluation" not in app.session_state
    # No coaching around the security check.
    assert "hint" not in app.session_state

    assert app.session_state["recommendation"].decision == "reinforce"


def test_failed_submission_gets_a_hint():
    app = submit(run_app(), failing_code)
    assert app.session_state["history"][-1]["result"] == "failed"
    assert "hint" in app.session_state


def test_error_submission_gets_a_hint():
    """An unparseable submission still deserves guidance — just not a grade."""
    app = submit(run_app(), error_code)
    assert "hint" in app.session_state
    assert "evaluation" not in app.session_state


# --- navigation ------------------------------------------------------------


def test_advancing_clears_the_previous_question():
    app = submit(run_app(), passing_code)
    next_id = app.session_state["recommendation"].next_question_id

    advance(app)

    assert current_id(app) == next_id
    assert next_id in app.session_state["served"]
    # Stale results from the previous question must not leak onto the new one.
    for key in ("sandbox_result", "hint", "evaluation", "recommendation"):
        assert key not in app.session_state, f"{key} leaked across questions"
    # History survives — it is the feature source.
    assert len(app.session_state["history"]) == 1


def test_never_reserves_a_served_question():
    app = run_app()
    for _ in range(3):
        submit(app, failing_code)
        advance(app)

    served = app.session_state["served"]
    assert len(served) == len(set(served)), f"repeat served: {served}"


def test_provider_is_the_contract_value():
    """client.py raises on anything but 'ollama'/'openai' — not the UI label."""
    app = run_app()
    assert app.session_state["model_provider"] in ("ollama", "openai")


def test_baseline_mode_switch():
    app = run_app()
    app.sidebar.checkbox[0].set_value(True).run()
    submit(app, passing_code)
    # The rules baseline reports full confidence by construction.
    assert app.session_state["recommendation"].confidence == 1.0


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("\napp integration checks passed")
