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
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Must be set before app.py is imported: it selects evaluator.stub over the real
# LLM path, so the suite runs offline and fast. The stub's hardcoded 4/5 is what
# the score assertions below deliberately pin.
os.environ["EVALUATOR_MODE"] = "stub"

from streamlit.testing.v1 import AppTest  # noqa: E402

from contracts.types import LLMEvaluation, LLMHint  # noqa: E402
from recommender import engine  # noqa: E402
from ui import history as ui_history  # noqa: E402
from ui.sidebar import OTHER as OTHER_LABEL  # noqa: E402

# data/predictions.jsonl is the Week 13 evaluation dataset — keep test runs out.
engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_apptest.jsonl"

# Same for session transcripts: test sessions must not land in data/sessions/.
SESSIONS_TMP = Path(tempfile.mkdtemp(prefix="sessions_"))
ui_history.SESSIONS_DIR = SESSIONS_TMP

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


def sidebar_input(app, label):
    """Find a sidebar text input by label — position shifts as fields change."""
    for field in app.sidebar.text_input:
        if field.label == label:
            return field
    raise AssertionError(
        f"no sidebar input {label!r}; have {[f.label for f in app.sidebar.text_input]}"
    )


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


def test_byom_config_is_assembled():
    """The evaluator reads one dict. client.py does byom_config.get('provider'),
    so passing a bare string here is an AttributeError on the first submission."""
    app = run_app()
    config = app.session_state["byom_config"]

    assert isinstance(config, dict), config
    # client.py raises ValueError on anything but these — not the UI label.
    assert config["provider"] in ("ollama", "openai"), config
    assert config["model"], "a model name is required by evaluator.client"
    assert "api_key" in config
    # base_url is what lets a user point at their own server / own model.
    assert "base_url" in config


def test_any_model_name_is_accepted():
    """BYOM means any model the user has pulled — qwen, deepseek, whatever —
    not a fixed dropdown. The local model field must be free text."""
    app = run_app()

    # With no local server reachable the picker falls back to a text input.
    sidebar_input(app, "Model name").set_value("qwen2.5-coder:7b").run()

    assert app.session_state["byom_config"]["model"] == "qwen2.5-coder:7b"


def test_local_server_url_is_editable():
    """A model can live on another port or another machine."""
    from ui.sidebar import DEFAULT_LOCAL_URL, list_local_models

    app = run_app()
    assert app.session_state["byom_config"]["base_url"] == DEFAULT_LOCAL_URL

    # Discovery must degrade quietly on a server that has no /api/tags.
    assert list_local_models("http://localhost:9/v1") == []


def fake_ollama(models):
    """A stand-in Ollama serving /api/tags, so discovery is testable offline."""
    import http.server
    import threading

    payload = json.dumps({"models": [{"name": m} for m in models]}).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = payload if self.path == "/api/tags" else b"{}"
            self.send_response(200 if self.path == "/api/tags" else 404)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/v1"


def test_installed_models_are_discovered():
    """The sidebar should offer whatever the user has actually pulled —
    that is what makes 'bring your own model' concrete rather than a dropdown
    of three names somebody hardcoded."""
    from ui.sidebar import list_local_models

    server, url = fake_ollama(["qwen2.5-coder:7b", "deepseek-coder:6.7b", "gemma2"])
    try:
        assert list_local_models(url) == [
            "deepseek-coder:6.7b",
            "gemma2",
            "qwen2.5-coder:7b",
        ]

        # ...and picking one through the UI puts it in byom_config.
        app = run_app()
        sidebar_input(app, "Server URL").set_value(url).run()

        options = app.sidebar.selectbox[0].options
        assert "qwen2.5-coder:7b" in options, options
        assert OTHER_LABEL in options, "must always allow a name not in the list"

        app.sidebar.selectbox[0].set_value("qwen2.5-coder:7b").run()
        config = app.session_state["byom_config"]
        assert config["model"] == "qwen2.5-coder:7b"
        assert config["base_url"] == url
    finally:
        server.shutdown()


def test_evaluator_stub_and_real_share_a_signature():
    """app.py swaps these by env var, so their contracts must be identical."""
    import inspect

    from evaluator import grading, hints, stub

    def params(fn):
        return list(inspect.signature(fn).parameters)

    assert params(stub.evaluate_complexity) == params(grading.evaluate_complexity)
    assert params(stub.get_hint) == params(hints.get_hint)
    # ...and both must produce the frozen contract types, not dicts.
    config = {"provider": "ollama", "model": "gemma2"}
    assert isinstance(stub.evaluate_complexity("", {}, config), LLMEvaluation)
    assert isinstance(stub.get_hint("", {}, "", config), LLMHint)


def test_session_transcript_is_written():
    """data/sessions/<id>.json is the transcript source the Week 13
    evaluation plan depends on — it had no producer at all before this."""
    app = submit(run_app(), failing_code)

    session_id = app.session_state["session_id"]
    path = SESSIONS_TMP / f"{session_id}.json"
    assert path.exists(), f"no transcript at {path}"

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["session_id"] == session_id
    assert len(payload["history"]) == 1
    assert payload["provider"] in ("ollama", "openai")
    assert payload["history"][0]["question_id"] == "q_0001"
    # An API key must never reach disk.
    assert "api_key" not in json.dumps(payload)

    submit(app, failing_code)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["history"]) == 2, "transcript must grow with the session"


def test_evaluator_failure_does_not_break_the_session():
    """Ollama being down must not abort a submission or lose the attempt."""
    from evaluator import stub
    from evaluator.errors import EvaluatorError

    # app.py re-runs `from evaluator.stub import get_hint` on every script run,
    # so patching the module attribute is what reaches it.
    original = stub.get_hint

    def boom(*args, **kwargs):
        raise EvaluatorError("Couldn't reach the model.")

    stub.get_hint = boom
    try:
        app = run_app()
        app.text_area[0].set_value(failing_code(current_id(app)))
        app.button(key="submit_code_btn").click().run()
        assert not app.exception, app.exception
    finally:
        stub.get_hint = original

    # The friendly message is shown...
    assert any("reach the model" in str(e.value) for e in app.error), [
        str(e.value) for e in app.error
    ]
    # ...and the attempt is still recorded, unscored, and still routed.
    attempt = app.session_state["history"][-1]
    assert attempt["result"] == "failed"
    assert attempt["efficiency_score"] is None
    assert app.session_state["recommendation"].decision == "reinforce"


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
