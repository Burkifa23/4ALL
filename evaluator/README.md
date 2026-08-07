# evaluator — LLM hints & complexity grading (Person 2)

Wraps a BYOM (bring-your-own-model) LLM to produce two things: a nudge when a
submission fails, and a Big-O / efficiency / style grade when it passes.

Prompt iteration history is in [`docs/gemma_scoring_notes.md`](../docs/gemma_scoring_notes.md),
the V1 golden-set baseline in [`docs/day5_baseline.md`](../docs/day5_baseline.md),
and the bias-audit protocol in [`docs/ethics_audit_plan.md`](../docs/ethics_audit_plan.md).

## Public surface

```python
from evaluator.grading import evaluate_complexity
from evaluator.hints import get_hint

evaluation = evaluate_complexity(code, question, byom_config)  # -> LLMEvaluation
hint       = get_hint(code, question, failed_case_summary, byom_config)  # -> LLMHint
```

Both return the frozen dataclasses from [`contracts/types.py`](../contracts/types.py).

`byom_config` is assembled by `ui/sidebar.py` and read by `client.make_client`:

```python
{
    "provider": "ollama" | "openai",   # contract value, not the UI label
    "model":    "gemma2",              # any model name the server knows
    "api_key":  None,                  # cloud only
    "base_url": "http://localhost:11434/v1",   # local only; None = provider default
}
```

## Layout

| File | What |
|---|---|
| `client.py` | `make_client(byom_config)` + `complete(...)`. Maps every SDK exception to `EvaluatorError`. |
| `errors.py` | `EvaluatorError` with a student-facing `user_message`, and `map_error`. |
| `prompts.py` | Prompt constants. V2 grader system prompt is the live one. |
| `hints.py` | `get_hint` — nudges only, never the answer. |
| `grading.py` | `evaluate_complexity` — three-shot prompt, JSON retry, sha256 cache. |
| `parsing.py` | `parse_evaluation` — defensive; never raises, regex-salvages on bad JSON. |
| `stub.py` | Offline stand-in with identical signatures and return types. |
| `testing/` | Golden set, adversarial suite, bias audit. |

---

## Changes made by Person 3 on Aug 6 (integration fixes)

These were made to unblock the live app and the Week 13 recommender evaluation.
All are small; the reasoning is here so nothing looks like an unexplained edit.

### 1. Both entry points now return the frozen contract types

**Was:** `get_hint` returned `{"provider": ..., "hint_text": ...}` and
`evaluate_complexity` returned the dict straight from `parse_evaluation`.

**Problem:** `contracts/types.py` defines `LLMHint` and `LLMEvaluation`
dataclasses, frozen and signed off on Fri Jul 31, and `ui/results.py` reads
them by attribute (`.hint_text`, `.big_o_time`). Wiring the real evaluator into
`app.py` would have raised `AttributeError: 'dict' object has no attribute
'hint_text'` on the first failed submission. The contract was signed on types
nothing constructed.

**Now:** `hints.py` returns `LLMHint(...)`; `grading.py` returns
`LLMEvaluation(**parse_evaluation(...))`.

`parsing.parse_evaluation` deliberately **still returns a dict** — it is a
parser with other callers, and constructing the contract type belongs one layer
up. Two callers that indexed the old dict were updated to attribute access:
`testing/bias_audit/dry_run.py` and `scratch_test6.py`.

### 2. `stub.py` now matches the real signature

**Was:** `get_hint(code, question, failed_case_summary, provider)` — a bare
provider **string**, while the real functions take a `byom_config` **dict**.

**Problem:** the two were not interchangeable, so swapping them in `app.py` was
never a one-line change. `client.py` does `byom_config.get("provider")`, which
raises `AttributeError` on a string.

**Now:** both stub functions take `byom_config` and read `.get("provider")`.
`app.py` selects between stub and real with `EVALUATOR_MODE=stub`, and
`tests/test_app_integration.py::test_evaluator_stub_and_real_share_a_signature`
asserts the two keep matching parameter lists and return types.

Use the stub to run the app with no Ollama, and as the demo fallback:

```bash
EVALUATOR_MODE=stub streamlit run app.py
```

### 3. `client.py` honours a configurable `base_url`

**Was:** `base_url="http://localhost:11434/v1"` hardcoded for the local path.

**Problem:** that is Ollama-on-this-machine only. The project's BYOM claim means
a user should be able to run whatever model they like — qwen, deepseek-coder,
codellama — on whatever server they like.

**Now:** `base_url` is read from `byom_config` and defaults to the old value, so
existing behaviour is unchanged. Any OpenAI-compatible server works: Ollama on
another port or host, LM Studio (`http://localhost:1234/v1`), vLLM, llama.cpp.
The local `api_key` also falls back to `"ollama"` rather than being hardcoded,
since some local servers expect a real token.

### 4. `errors.py` maps "bad or unloadable model" to the server's own message

**Was:** `map_error` covered connection, auth, rate-limit and timeout. Everything
else fell through to *"Something went wrong while contacting the model."*

**Problem:** now that the sidebar accepts any model name against any server,
"this server can't give you that model" is the **most likely** failure mode, and
it landed in the generic bucket. Found while testing against LM Studio: asking
for a model that won't load produced a 400 whose body said exactly what was
wrong, and the UI replaced it with an apology.

```
BadRequestError 400
{"error": {"message": "No models loaded. Please load a model in the developer
 page or use the 'lms load' command.", "type": "invalid_request_error"}}
```

**Now:** a 400/404 whose message mentions the model passes the server's own text
through — *"The model couldn't be used: No models loaded... Check the model name
and Server URL in the sidebar."* Ollama's "model not found, try pulling it"
surfaces the same way. Covered by
`tests/test_app_integration.py::test_unusable_model_reports_the_servers_own_message`.

### 5. Bare Server URLs get `/v1`, and 200-with-an-error-body is caught

Both found from a real report of *"Something went wrong while contacting the
model"* against LM Studio.

**Cause.** LM Studio and Ollama both display their address as
`http://localhost:1234` — so that is what people paste into the sidebar. The
OpenAI SDK appends the route directly, producing `POST /chat/completions`
instead of `POST /v1/chat/completions`. LM Studio's log showed it plainly:

```
[ERROR] Unexpected endpoint or method. (POST /chat/completions). Returning 200 anyway
```

**Two separate defects, both fixed:**

1. `client.normalise_base_url` appends `/v1` when the URL is a bare host. An
   explicit path is left alone, since not every server is mounted at `/v1`.
2. **The SDK never raised.** LM Studio returns **HTTP 200** with an error body,
   so the SDK produced `ChatCompletion(choices=None, error='Unexpected
   endpoint...')` and `response.choices[0]` raised a `TypeError` — which
   `map_error` flattened into the generic apology. `complete()` now checks
   `response.choices` explicitly and surfaces the server's own text.

### 6. `EvaluatorError` carries technical `detail`

`user_message` stays student-facing; `detail` holds the exception type, HTTP
status, request URL and the server's message. `app.py` renders it in a collapsed
"Technical details" expander, so a student isn't shown a stack trace but whoever
is wiring up a model has something to act on. Every `map_error` branch populates
it, and the catch-all now says to open the details rather than just "try again".

Setup and troubleshooting for all of this:
[`docs/local_model_setup.md`](../docs/local_model_setup.md).

### 7. The provider name no longer decides the endpoint

**Was:** `make_client` branched on `provider`, hardcoding `"ollama"` → localhost
and `"openai"` → `api.openai.com`, and raising `ValueError` on anything else.
The sidebar matched: a URL field only on the local branch, a key field only on
the cloud branch.

**Problem:** any hosted OpenAI-compatible API that isn't OpenAI fitted neither
branch. Reported with Groq — a `gsk_...` key was sent to `api.openai.com` and
came back:

```
401 Incorrect API key provided: gsk_Ctnu****
Request URL: https://api.openai.com/v1/chat/completions
```

**Now:** `make_client` reads `base_url`, `api_key` and `model` and branches on
nothing. Any OpenAI-compatible endpoint works — Ollama, LM Studio, vLLM,
llama.cpp, OpenAI, Groq, OpenRouter, Together, DeepSeek, a company gateway.
Adding a provider is a row of data in `ui/sidebar.py::PRESETS`, never a code
change, and **Custom** covers anything not listed.

Three supporting changes:

- **`LEGACY_BASE_URLS`** keeps configs that pass a provider name and no
  `base_url` working — Person 2's `scratch_*.py` and `testing/` scripts all do
  this. It is a lookup table of defaults, not behaviour.
- **A missing URL now raises** rather than letting the SDK fall back to
  `api.openai.com`, which was the same wrong assumption one layer down.
- **`list_models(byom_config)`** replaces the Ollama-specific `/api/tags` probe
  with the OpenAI-standard `GET /v1/models`, which Ollama, LM Studio, OpenAI,
  Groq and OpenRouter all implement — one code path instead of per-provider
  special cases. Returns `[]` on failure, so the UI falls back to free text and
  nothing is ever gated behind the list.

`contracts/types.py` widened `provider` from `Literal["ollama", "openai"]` to a
free-text label, so a Groq run records `"groq"` instead of being mislabelled
`"openai"`. Widening only — every previously valid value still is — and it
matters because provider provenance feeds the Week 13 evaluation.

### 8. Model discovery explains itself, and a bad model name lists the real ones

**Was:** `list_models` returned `[]` on any failure. The sidebar then said
*"This endpoint doesn't publish a model list"* and gave a free-text field.

**Problem:** for a hosted provider that message is usually **wrong**. Groq does
publish a list — it just 401s without a key, and most providers do the same. So
the user was told the wrong thing and left typing a model id blind, which is
exactly how `grok` (xAI's chatbot, not a Groq model id) got submitted and came
back `404 model_not_found`.

**Now:**

- `fetch_models(config)` returns `(models, reason)` and the sidebar shows the
  reason — *"the API key was rejected (401)"*, *"this endpoint has no /models
  listing (404)"*, or the connection error. `list_models` remains as a thin
  wrapper for existing callers.
- A **Refresh model list** button bypasses the cache, for after pasting a key or
  loading a model in LM Studio.
- When a call fails and the chosen model isn't in the endpoint's list, `app.py`
  **prints the available models** under the error. The endpoint knows the right
  answer; the user shouldn't have to go hunting through provider docs.

---

## Still outstanding (Person 2's, untouched)

Listed from the Week 12 audit so nothing gets lost — **not** done by Person 3:

- `testing/run_golden.py` is **0 bytes**. The golden harness is a recurring duty
  after any prompt or parser change; its work currently lives in the root
  `scratch_*.py` files.
- **Fallback rate is never measured.** `parse_evaluation`'s regex path logs
  nothing, so the "≤5% fallback" acceptance criterion can't be evidenced. The
  regex grabs the first two `1-5` digits anywhere in the text, so a preamble
  like "2 issues with your 3 loops" scores `efficiency=2, style=3` and looks
  real to the recommender.
- **Cache key omits the prompt version** (`_cache_key` is `code|question_id|model`),
  so iterating the grader prompt returns stale scores for repeat solutions.
- `GRADER_PROMPT_V1_USER_TEMPLATE` is imported by `grading.py` and unused — the
  three-shot user prompt is an inline f-string, so "all prompts live in
  prompts.py, versioned" is not currently true. No version-history table either.
- Bias-audit variant set is **3 solutions**; `docs/ethics_audit_plan.md` plans 8.
  `dry_run.py` hardcodes one provider where the plan says both.
- `__init__.py` is empty, so `import evaluator; evaluator.get_hint` fails.
