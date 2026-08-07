
# Adaptive AI Coding Assessment Platform

## Team Members

- Chuong – Sandbox
- Person 2 – LLM Evaluator
- Person 3 – Recommender
- Person 4 – Frontend & Integration

## Setup

1. Clone the repository.
2. Create and activate a virtual environment:

```bash
python -m venv venv
```

```bash
venv\Scripts\activate
```

(macOS/Linux: `source venv/bin/activate`)

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
streamlit run app.py
```

Run it without any model — hints and grades come from a fixed stand-in, so the
question flow and the recommender still work:

```bash
EVALUATOR_MODE=stub streamlit run app.py
```

Run the tests:

```bash
python tests/test_app_integration.py
```

```bash
python tests/test_recommender.py
```


> **Setting up a model?** Read **[docs/local_model_setup.md](docs/local_model_setup.md)** —
> Ollama, LM Studio, OpenAI cloud, running with no model at all, and a
> troubleshooting section for every error the app can show.

## Local Model Setup (Ollama)

This project can run using a local AI model instead of a paid cloud API. Here's how to get that working on your machine.

### 1. Install Ollama

Download and install Ollama from [ollama.com](https://ollama.com) — pick the version for your operating system and run the installer. Once installed, it runs quietly in the background (on Windows, look for its icon in the system tray near the clock).

### 2. Download a model

Open a terminal and run:

```bash
ollama pull gemma2
```

This downloads the model the team's reported results are based on (`gemma2`).
It's a few gigabytes, so it may take a while.

**For reproducing the report's numbers, everyone should use `gemma2`** — the
golden-set baselines and the bias audit were measured against that exact tag,
and a different model gives different scores.

**For everyday use, bring whatever model you like.** The sidebar lists whatever
`ollama list` shows and accepts any name you type, so `qwen2.5-coder`,
`deepseek-coder`, `codellama` and friends all work:

```bash
ollama pull qwen2.5-coder
```

You are not limited to Ollama either — see "Using a different server" below.

### 3. Verify it works

Once the download finishes, test it with: ollama run gemma2 "Say hello in 5 words"

If you get a text response back, Ollama is working correctly. Type `/bye` to exit.

### 4. Verify the app's connection method

The app talks to Ollama using the OpenAI Python SDK, pointed at Ollama's local address instead of OpenAI's servers. You can confirm this works with a quick test script:

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

resp = client.chat.completions.create(
    model="gemma2",
    messages=[{"role": "user", "content": "Say hello in 5 words"}],
    temperature=0.2,
)
print(resp.choices[0].message.content)
```

If this prints a response, your setup is complete and the app will be able to reach the local model.

### Using a different server

The **Server URL** field in the sidebar accepts any OpenAI-compatible endpoint,
so the model does not have to be Ollama or even on your machine:

| Server | URL |
|---|---|
| Ollama (default) | `http://localhost:11434/v1` |
| LM Studio | `http://localhost:1234/v1` |
| vLLM / llama.cpp | whatever port you started it on |
| Ollama on another machine | `http://<their-ip>:11434/v1` |

If the server answers Ollama's `/api/tags`, the sidebar lists its installed
models for you to pick from. If it doesn't (LM Studio, vLLM), you just type the
model name — nothing is gated behind the list.

### Cloud model

Choose "OpenAI Cloud" in the sidebar, type any model name (`gpt-4o-mini` by
default) and paste an API key. Put `OPENAI_API_KEY=...` in a `.env` file
(see `.env.example`) and the field fills itself. Keys live in the browser
session only and are never written to disk or into a session transcript.

### Troubleshooting

- **"Couldn't reach the model"** — Ollama isn't running. Check your system tray, or start it manually by running `ollama serve` in a terminal. The app shows this as a friendly message and keeps the session going; your submission is still graded by the sandbox and still routed.
- **Model not found** — run `ollama list` to see what's installed, and make sure the name in the sidebar matches exactly (tags matter: `qwen2.5-coder:7b` is not `qwen2.5-coder`).
- **No models listed in the sidebar** — either the server is down, or it isn't Ollama. Type the model name directly; that always works.
- **It's slow** — local models take 20–90 s per call on CPU. Use `EVALUATOR_MODE=stub` when you're working on the UI or the recommender and don't need real grades.

---

## Changes made by Person 3 on Aug 6 (frontend & integration)

Recorded here because these touch `app.py` and `ui/`, which are Person 4's
files. Each was needed to make the recommender's Week 13 evaluation possible.
Evaluator-side changes are documented in
[`evaluator/README.md`](evaluator/README.md).

### The blocking one: the app was using the stub evaluator

`app.py` imported `evaluator.stub`, so **every graded submission returned a
hardcoded `efficiency_score=4, style_score=5`**. Four of the recommender's
features were therefore constants in every logged decision, and the rules
baseline it is measured against keys on `last_efficiency_score >= 3` — always
true under the stub. The Week 13 comparison would have measured nothing.

The real evaluator is now wired, with `EVALUATOR_MODE=stub` selecting the
offline stand-in for tests and for demoing without a model.

### `ui/sidebar.py` — a real `byom_config`

It stored only `st.session_state["model_provider"]`, a bare **string**, while
all of Person 2's code expects a `byom_config` **dict**
(`client.py` calls `byom_config.get("provider")`). There was also no model
selector and no API-key input anywhere, so the cloud path — the project's
accessibility claim — was unreachable from the UI.

Now builds `st.session_state["byom_config"]` with provider, model, api_key and
base_url, adding a server-URL field, model discovery from `ollama list`, and a
masked key input pre-filled from `OPENAI_API_KEY` (`load_dotenv()` is now
called, so `.env` finally takes effect).

The provider stored is the contract value (`"ollama"` / `"openai"`), **not** the
display label. It was previously storing `"Local Ollama (Gemma)"`, which
`evaluator/client.py` rejects with `ValueError: Unknown provider` — invisible
against the stub, a crash the moment the real client was used.

### `app.py` — error handling and progress

There was no `try`/`except` anywhere in `app.py` or `ui/`, while
`evaluator/errors.py` already provided `EvaluatorError.user_message` with
student-facing text, unused. With the real evaluator wired, Ollama being down
would have put a red traceback on the demo screen.

Both LLM calls are now wrapped, showing `exc.user_message` via `st.error`. A
model failure never aborts the submission: the attempt is still recorded
unscored and still routed, which the recommender handles via its cold-start
defaults. `st.spinner` was added around the sandbox run and both LLM calls —
the hint path has a 150-second timeout and used to freeze the UI silently.

### `ui/history.py` — session persistence

The app wrote **nothing** to disk; history died with the browser tab. `docs/evaluation_plan_recommender.md`
names `data/sessions/*.json` as a Week 13 data source and it had no producer.

`save_session()` now writes the transcript on every attempt. It records
provider, model and base_url as provenance and **never writes `api_key`** —
there is a test asserting no key reaches disk. Write failures are swallowed:
losing a transcript must not end a student's assessment.

`add_attempt` also gained an `evaluation` parameter so the attempt's efficiency
and style scores are recorded. Without it, four of the recommender's features
had no source at all.

### `ui/results.py` — show what the student is graded on

Only `big_o_time` and `efficiency_score` were rendered. `style_score` and
`raw_feedback` were collected and fed to the recommender but never shown, so
students were routed on a dimension they couldn't see. Both now appear, with
the scores as `st.metric` and the feedback in an expander.

### `tests/test_app_integration.py`

Runs the real `app.py` headlessly via `streamlit.testing.v1.AppTest` against the
real sandbox — 23 checks including the two behavioural acceptance tests, the
"errors must not raise difficulty" regression, transcript persistence, and
graceful degradation when the model is unreachable. It sets `EVALUATOR_MODE=stub`
so it stays offline and fast, and redirects both `data/predictions.jsonl` and
`data/sessions/` to temp so test runs never pollute evaluation data.

### Known issues left for Person 4

Not fixed, and worth doing before the freeze:

- **No git tags exist at all** — `v0.1-shell` and `v0.2-sprint1` were never cut.
- `requirements.txt` is **unpinned** and missing `datasets`, which
  `data/ingest/ingest_leetcode.py` imports. A scikit-learn bump can break
  `joblib.load` on the trained model mid-demo.
- `.gitignore` ignores `.streamlit/`, so a committed theme is impossible, while
  `data/questions/` is ignored *and* tracked — regenerated questions are
  invisible to `git add`.
- Question paths are CWD-relative (`Path("data/questions")`), so running
  `streamlit run app.py` from anywhere but the repo root gives an `IndexError`.
- `ui/history.py::get_history()` is dead code.
- **No test users are booked for Aug 10**, and no names are assigned to any task
  in `docs/evaluation_plan_recommender.md`. This is the highest-risk open item
  on the project.



