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
