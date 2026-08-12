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

# And for the provenance copy of generated questions, and broken-test reports.
from evaluator import generate as evaluator_generate  # noqa: E402
from ui import results as ui_results  # noqa: E402

evaluator_generate.GENERATED_DIR = Path(tempfile.mkdtemp(prefix="generated_"))
ui_results.REPORTS_PATH = Path(tempfile.mkdtemp(prefix="reports_")) / "reports.jsonl"

# The model-written question fixture lives with the checks that own it.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_generated_question import record as generated_record  # noqa: E402

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


def sidebar_selectbox(app, label):
    for field in app.sidebar.selectbox:
        if field.label == label:
            return field
    raise AssertionError(
        f"no sidebar selectbox {label!r}; "
        f"have {[f.label for f in app.sidebar.selectbox]}"
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


# --- custom practice: a detour must not become a rung on the ladder --------


def serve_generated(app):
    """Put the app in the state Custom Practice leaves it in.

    Deliberately not calling generate_question(): that needs a model, and what
    is under test here is the routing, not the generating. app.py re-registers
    from session_state on every rerun, so this exercises the real path.
    """
    record = generated_record()
    app.session_state["generated"] = {record["question_id"]: record}
    app.session_state["current_question_id"] = record["question_id"]
    app.session_state["served"].append(record["question_id"])
    app.run()
    assert not app.exception, app.exception
    return record


def test_generated_question_is_served_and_runnable():
    app = run_app()
    record = serve_generated(app)

    assert current_id(app) == record["question_id"]

    # It was never written to data/questions/, so this only works because
    # app.py registered it with the sandbox.
    app.text_area[0].set_value(record["reference_solution"])
    app.button(key="submit_code_btn").click().run()
    assert not app.exception, app.exception

    result = app.session_state["sandbox_result"]
    assert result.status == "passed", result
    assert result.tests_total == record["test_case_count"]


def test_generated_question_does_not_move_the_ladder():
    """The bypass: a model-written question's difficulty and topic must not
    drive the next routing decision, but the attempt still counts."""
    app = submit(run_app(), failing_code)  # one real attempt on q_0001

    assert app.session_state["anchor_question_id"] == "q_0001"

    record = serve_generated(app)

    app.text_area[0].set_value(record["reference_solution"])
    app.button(key="submit_code_btn").click().run()
    assert not app.exception, app.exception

    # The work counts: the attempt is in history under its own id.
    attempt = app.session_state["history"][-1]
    assert attempt["question_id"] == record["question_id"]
    assert attempt["result"] == "passed", attempt

    # The routing does not: the decision was made from the anchor.
    assert app.session_state["anchor_question_id"] == "q_0001"

    logged = json.loads(engine.PREDICTION_LOG.read_text().strip().splitlines()[-1])
    vector = logged["vector"]

    assert vector["question_id"] == "q_0001", vector
    assert vector["question_difficulty"] == 1, "a generated 'Medium' is not a rung"
    assert vector["question_topic"] == QUESTIONS["q_0001"]["topic"]

    # The detour neither reset nor inflated the anchor's attempt count...
    assert vector["attempts_on_question"] == 1, vector
    # ...but its outcome did carry into the decision.
    assert vector["last_attempt_passed"] is True, vector

    # And the question served next is a real one.
    assert logged["next_question_id"] in QUESTIONS

    advance(app)
    assert current_id(app) in QUESTIONS
    assert app.session_state["anchor_question_id"] == current_id(app)


def test_reporting_a_broken_test_logs_it_and_can_discard_the_question():
    """The backstop for a question that is self-consistent but still wrong."""
    app = run_app()
    record = serve_generated(app)

    method = record["entry_point"].split(".")[-1]
    app.text_area[0].set_value(
        f"class Solution:\n    def {method}(self, *args, **kwargs):\n        return None\n"
    )
    app.button(key="submit_code_btn").click().run()

    app.button(key="report_broken_test_btn").click().run()
    assert not app.exception, app.exception

    logged = json.loads(ui_results.REPORTS_PATH.read_text().strip().splitlines()[-1])
    assert logged["question_id"] == record["question_id"]
    assert logged["generated"] is True
    assert logged["code"], "a report without the submission is unactionable"

    # Only generated questions can be discarded — a curated one has a verified
    # solution behind it, so the answer there is to keep trying.
    app.button(key="discard_btn").click().run()
    assert not app.exception, app.exception

    assert current_id(app) == app.session_state["anchor_question_id"]
    assert current_id(app) in QUESTIONS


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
    assert config["provider"], config
    assert config["model"], "a model name is required by evaluator.client"
    assert "api_key" in config
    # base_url is what lets a user point at their own server / own model.
    assert config["base_url"], "every provider needs an endpoint, not just local"


def test_any_model_name_is_accepted():
    """BYOM means any model the user has pulled — qwen, deepseek, whatever —
    not a fixed dropdown. The model field must be free text."""
    app = run_app()

    # With no local server reachable the picker falls back to a text input.
    sidebar_input(app, "Model name").set_value("qwen2.5-coder:7b").run()

    assert app.session_state["byom_config"]["model"] == "qwen2.5-coder:7b"


def test_every_provider_gets_a_url_and_a_key_field():
    """The old design gave a URL only to the local branch and a key only to the
    cloud branch, so a hosted non-OpenAI provider fitted neither."""
    from ui.sidebar import DEFAULT_LOCAL_URL, PRESETS

    app = run_app()
    assert app.session_state["byom_config"]["base_url"] == DEFAULT_LOCAL_URL

    labels = [f.label for f in app.sidebar.text_input]
    assert "Server URL" in labels and "API key" in labels, labels

    for name, preset in PRESETS.items():
        app.sidebar.selectbox[0].set_value(name).run()
        config = app.session_state["byom_config"]

        assert config["provider"] == preset["provider"]
        assert config["base_url"] == preset["base_url"]
        assert "Server URL" in [f.label for f in app.sidebar.text_input]
        assert "API key" in [f.label for f in app.sidebar.text_input]

    # Presets are starting points: the URL is editable for every one of them.
    app.sidebar.selectbox[0].set_value("Groq").run()
    sidebar_input(app, "Server URL").set_value("https://my-gateway.internal/v1").run()
    assert (
        app.session_state["byom_config"]["base_url"]
        == "https://my-gateway.internal/v1"
    )


def fake_endpoint(models, chat_error=None, require_key=None):
    """A stand-in OpenAI-compatible server, so BYOM is testable offline.

    models: what GET /v1/models reports. Pass None to omit the endpoint, which
        is how some servers (llama.cpp, older vLLM) behave.
    chat_error: message to return as a 400 from /v1/chat/completions.
    require_key: if set, requests without this bearer token get a 401.
    """
    import http.server
    import threading

    listing = (
        json.dumps(
            {"object": "list", "data": [{"id": m, "object": "model"} for m in models]}
        ).encode()
        if models is not None
        else None
    )
    error_body = json.dumps(
        {"error": {"message": chat_error, "type": "invalid_request_error"}}
    ).encode()

    class Handler(http.server.BaseHTTPRequestHandler):
        def _send(self, status, body):
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authorised(self):
            if require_key is None:
                return True
            return self.headers.get("Authorization") == f"Bearer {require_key}"

        def do_GET(self):
            if not self._authorised():
                self._send(401, b'{"error": {"message": "bad key"}}')
            elif self.path == "/v1/models" and listing is not None:
                self._send(200, listing)
            else:
                self._send(404, b"{}")

        def do_POST(self):
            if not self._authorised():
                self._send(401, b'{"error": {"message": "bad key"}}')
            else:
                self._send(400, error_body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}/v1"


def test_server_without_a_model_list_falls_back_to_free_text():
    """Not every OpenAI-compatible server implements /v1/models. Discovery must
    come up empty rather than erroring, so the free-text field is used."""
    from evaluator.client import list_models

    server, url = fake_endpoint(models=None)
    try:
        assert list_models({"base_url": url}) == []

        app = run_app()
        sidebar_input(app, "Server URL").set_value(url).run()
        sidebar_input(app, "Model name").set_value("gemma-4-e2b-it").run()

        assert app.session_state["byom_config"]["model"] == "gemma-4-e2b-it"
        assert app.session_state["byom_config"]["base_url"] == url
    finally:
        server.shutdown()


def test_any_openai_compatible_provider_works():
    """The regression that prompted this: a Groq key was sent to
    api.openai.com and rejected 401, because the provider NAME chose the
    endpoint. The URL must decide, and nothing else."""
    from evaluator.client import make_client

    # A hosted provider that is not OpenAI, with its own key.
    server, url = fake_endpoint(models=["llama-3.3-70b-versatile"], require_key="gsk_x")

    try:
        config = {
            "provider": "groq",
            "base_url": url,
            "api_key": "gsk_x",
            "model": "llama-3.3-70b-versatile",
        }
        client = make_client(config)
        assert str(client.base_url).rstrip("/") == url.rstrip("/"), client.base_url

        from evaluator.client import list_models

        assert list_models(config) == ["llama-3.3-70b-versatile"]

        # ...and the wrong key is rejected by that server, not by OpenAI's.
        assert list_models({**config, "api_key": "wrong"}) == []
    finally:
        server.shutdown()


def test_provider_name_never_picks_the_endpoint():
    """No provider name may be special-cased. An unknown one with a URL works;
    a known one still honours an overriding URL."""
    from evaluator.client import make_client

    invented = make_client(
        {"provider": "something-nobody-has-heard-of", "base_url": "http://x.test/v1"}
    )
    assert str(invented.base_url).rstrip("/") == "http://x.test/v1"

    # "openai" must not force api.openai.com when a URL is given.
    overridden = make_client({"provider": "openai", "base_url": "http://y.test/v1"})
    assert "openai.com" not in str(overridden.base_url)


def test_discovery_failure_says_why():
    """A silent empty list leaves the user typing a model name blind — which is
    how a typo becomes a 404 at submission time. Report the reason."""
    from evaluator.client import fetch_models

    # key rejected
    server, url = fake_endpoint(models=["a"], require_key="right")
    try:
        models, reason = fetch_models({"base_url": url, "api_key": "wrong"})
        assert models == []
        assert "401" in reason, reason

        models, reason = fetch_models({"base_url": url, "api_key": "right"})
        assert models == ["a"] and reason is None
    finally:
        server.shutdown()

    # endpoint has no listing at all
    server, url = fake_endpoint(models=None)
    try:
        models, reason = fetch_models({"base_url": url})
        assert models == []
        assert "404" in reason, reason
    finally:
        server.shutdown()

    # unreachable
    models, reason = fetch_models({"base_url": "http://127.0.0.1:9/v1"})
    assert models == [] and reason


def test_wrong_model_name_is_shown_the_real_options():
    """The endpoint knows which models exist; the user should not have to go
    hunting through provider docs after a 404."""
    from evaluator.client import fetch_models

    server, url = fake_endpoint(
        models=["llama-3.3-70b-versatile", "openai/gpt-oss-120b"],
        chat_error="The model `grok` does not exist",
    )
    try:
        config = {"provider": "groq", "base_url": url, "model": "grok"}
        available, reason = fetch_models(config)

        assert reason is None
        assert config["model"] not in available
        # this is what app.py puts in front of the user
        assert "llama-3.3-70b-versatile" in available
    finally:
        server.shutdown()


def test_missing_url_fails_loudly_instead_of_defaulting_to_openai():
    """The SDK silently defaults to api.openai.com when base_url is None, which
    reintroduces the same wrong assumption one layer down — a Groq key would be
    sent to OpenAI and rejected 401."""
    from evaluator.client import make_client
    from evaluator.errors import EvaluatorError

    try:
        make_client({"provider": "custom", "base_url": "", "api_key": "gsk_x"})
        raise AssertionError("expected an EvaluatorError")
    except EvaluatorError as exc:
        assert "server URL" in exc.user_message, exc.user_message


def test_bare_host_url_gets_the_v1_suffix():
    """LM Studio and Ollama both display their address without /v1, so that is
    what people paste — and the SDK then posts to /chat/completions, which LM
    Studio answers with HTTP 200 and an error body. Normalise it instead."""
    from evaluator.client import normalise_base_url

    assert normalise_base_url("http://localhost:1234") == "http://localhost:1234/v1"
    assert normalise_base_url("http://localhost:1234/") == "http://localhost:1234/v1"
    # already correct, and explicit paths are left alone
    assert normalise_base_url("http://localhost:1234/v1") == "http://localhost:1234/v1"
    assert normalise_base_url("http://host/custom/path") == "http://host/custom/path"
    assert normalise_base_url("") == ""


def test_a_200_with_no_completion_is_not_silently_swallowed():
    """Some local servers report failure as 200 + an error body. `choices` is
    then None, and indexing it used to raise a TypeError that map_error
    flattened into 'something went wrong'."""
    from evaluator.client import complete
    from evaluator.errors import EvaluatorError

    class FakeCompletions:
        def create(self, **kwargs):
            class Response:
                choices = None
                error = "Unexpected endpoint or method. (POST /chat/completions)"

            return Response()

    class FakeClient:
        chat = type("chat", (), {"completions": FakeCompletions()})()

    try:
        complete(client=FakeClient(), model="m", system="s", user="u")
        raise AssertionError("expected an EvaluatorError")
    except EvaluatorError as exc:
        assert "no completion" in exc.user_message
        assert "/v1" in exc.user_message, "must point at the actual cause"
        assert "Unexpected endpoint" in exc.detail, exc.detail


def test_every_error_carries_technical_detail():
    """The UI shows detail in an expander. Without it every misconfiguration
    produces the same sentence and there is nothing to act on."""
    import httpx
    from openai import APIConnectionError, APITimeoutError

    from evaluator.errors import map_error

    request = httpx.Request("POST", "http://localhost:1234/v1/chat/completions")

    for exc in (
        APIConnectionError(request=request),
        APITimeoutError(request=request),
        RuntimeError("something unexpected"),
    ):
        mapped = map_error(exc)
        assert mapped.detail, f"no detail for {type(exc).__name__}"
        assert type(exc).__name__ in mapped.detail

    # the catch-all must stop telling the user only to "try again"
    generic = map_error(RuntimeError("boom"))
    assert "details below" in generic.user_message


def test_unusable_model_reports_the_servers_own_message():
    """With free-text model names, 'this server can't give you that model' is
    the most likely failure. The server's message is far more actionable than
    a generic apology, so it must reach the student."""
    from evaluator.client import complete, make_client
    from evaluator.errors import EvaluatorError

    server, url = fake_endpoint(models=None, chat_error="No models loaded.")
    try:
        config = {"provider": "ollama", "model": "nope", "base_url": url}
        try:
            complete(
                client=make_client(config),
                model="nope",
                system="s",
                user="u",
                timeout=10,
            )
            raise AssertionError("expected the 400 to raise")
        except EvaluatorError as exc:
            assert "No models loaded." in exc.user_message, exc.user_message
            assert "sidebar" in exc.user_message
    finally:
        server.shutdown()


def test_available_models_are_discovered():
    """The sidebar should offer whatever the endpoint actually serves — that is
    what makes 'bring your own model' concrete rather than a dropdown of names
    somebody hardcoded. Works via the OpenAI-standard /v1/models, so the same
    code covers Ollama, LM Studio, Groq and OpenRouter alike."""
    from evaluator.client import list_models

    server, url = fake_endpoint(["qwen2.5-coder:7b", "deepseek-coder:6.7b", "gemma2"])
    try:
        assert list_models({"base_url": url}) == [
            "deepseek-coder:6.7b",
            "gemma2",
            "qwen2.5-coder:7b",
        ]

        # ...and picking one through the UI puts it in byom_config.
        app = run_app()
        sidebar_input(app, "Server URL").set_value(url).run()

        picker = sidebar_selectbox(app, "Model")
        assert "qwen2.5-coder:7b" in picker.options, picker.options
        assert OTHER_LABEL in picker.options, "must always allow a name not listed"

        picker.set_value("qwen2.5-coder:7b").run()
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
