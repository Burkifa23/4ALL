# Setting up a model

The app needs a language model to grade solutions and write hints.

**Any OpenAI-compatible API works.** The app never decides anything from the
provider's *name* — only three things matter, all set in the sidebar:

| Field | What it is |
|---|---|
| **Server URL** | the endpoint, usually ending in `/v1` |
| **API key** | blank for local servers, required for hosted ones |
| **Model** | picked from the endpoint's list, or typed |

The provider dropdown just pre-fills those three fields. Every one is editable,
and **Custom** starts blank, so a provider nobody listed still works.

| Option | Cost | Setup |
|---|---|---|
| **No model** (`EVALUATOR_MODE=stub`) | free | none — see [§4](#4-running-with-no-model-at-all) |
| **Local model** (Ollama or LM Studio) | free, runs on your machine | [§1](#1-ollama) or [§2](#2-lm-studio) |
| **Hosted API** (Groq, OpenAI, OpenRouter, Together, …) | needs an API key | [§3](#3-hosted-apis) |

---

## 1. Ollama

**Install.** Download from [ollama.com](https://ollama.com) and run the
installer. It runs in the background (Windows: check the system tray).

**Pull a model.**

```bash
ollama pull gemma2
```

Any model works — `qwen2.5-coder`, `deepseek-coder`, `codellama`. Use `gemma2`
if you are reproducing the numbers in the report, since that is what the
evaluator and the recommender's training data were calibrated against.

**Check it's running.**

```bash
ollama list
```

If that errors, start the server:

```bash
ollama serve
```

**In the sidebar:** choose *Local model*, leave the Server URL at
`http://localhost:11434/v1`, and pick your model from the list. Ollama reports
what it has installed, so the dropdown fills itself.

---

## 2. LM Studio

**Install** from [lmstudio.ai](https://lmstudio.ai).

**Download a model** from the Discover tab. Download the **main GGUF file** —
if the repo also offers files named `mmproj-*` (vision/audio projector) or
`mtp-*` (multi-token-prediction head), those are *accessories*, not the model.
Downloading only those gives you a model that fails to load with a message like
`requires ctx_other to be set`.

A file that is only tens of MB is not a language model. Expect 1–5 GB.

**Load the model and start the server.** On the **Developer** tab, load the
model, then toggle the server on. Or from a terminal:

```bash
lms server start
```

```bash
lms load <model-name>
```

`lms ls` shows what you have and which one is loaded.

**In the sidebar:** choose *Local model*, set the Server URL to
`http://localhost:1234/v1`, and **type the model name** — LM Studio does not
publish a model list the way Ollama does, so the dropdown falls back to a text
field. That is expected.

Use the exact id the server reports:

```bash
curl http://localhost:1234/v1/models
```

It is often namespaced, e.g. `google/gemma-4-e2b`, not `gemma-4-e2b`.

---

## 3. Hosted APIs

Pick the provider in the sidebar, check the Server URL it fills in, paste your
API key, and choose a model. Presets:

| Provider | Server URL | Key from |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `OPENAI_API_KEY` |
| Groq | `https://api.groq.com/openai/v1` | `GROQ_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| Together | `https://api.together.xyz/v1` | `TOGETHER_API_KEY` |
| Custom | *(you type it)* | `LLM_API_KEY` |

**Not listed?** Choose **Custom**, paste the provider's OpenAI-compatible base
URL and your key. DeepSeek, Mistral, Fireworks, Cerebras, a university gateway —
all work, because nothing in the code branches on who the provider is.

**Enter the key before picking the model.** Most providers require a valid key
even to *list* their models — Groq returns 401 on `/v1/models` without one. So
the Model field starts as free text and becomes a dropdown once the key is in.
If it doesn't switch, press **Refresh model list**.

Always pick from the dropdown rather than typing. Model ids are exact and
providers retire them: `grok` is not a Groq model (that's xAI's chatbot), and
Groq's own ids look like `llama-3.3-70b-versatile` or `openai/gpt-oss-120b`. If
you submit a name the endpoint doesn't have, the app now lists the ones it does.

To avoid retyping the key, copy `.env.example` to `.env` and set the variable
for your provider, e.g.:

```
GROQ_API_KEY=gsk_...
```

The key field fills itself from there. Keys live in the browser session only —
never written to disk, and never into a session transcript.

---

## 4. Running with no model at all

For working on the UI or the recommender, or if the model dies during a demo:

```bash
EVALUATOR_MODE=stub streamlit run app.py
```

Hints and grades come from a fixed stand-in (efficiency 4, style 5). Everything
else — the sandbox, the question flow, the adaptive routing — behaves normally.

---

## Any other server

The Server URL accepts **any OpenAI-compatible endpoint**, so vLLM, llama.cpp's
server, text-generation-webui, or a model on another machine all work:

```
http://localhost:8000/v1
http://192.168.1.42:11434/v1     # Ollama on a teammate's machine
```

If the server does not implement Ollama's `/api/tags`, the model dropdown falls
back to a text field. Nothing is gated behind the list.

---

## 5. CodeGenTutor — the question generator

The sidebar's **Custom Practice** form writes a brand-new question for any topic
you type, instead of serving one of the 50 in `data/questions/`. It needs a model
that returns the app's question schema as JSON, which is what
[`notebooks/finetune_codegen_tutor.ipynb`](../notebooks/finetune_codegen_tutor.ipynb)
fine-tunes on Google Colab.

Once the notebook has produced `codegen-tutor.Q4_K_M.gguf` (~2 GB):

1. Put it in `models/` next to `Modelfile.codegen-tutor`. Unsloth exports it as
   `unsloth.Q4_K_M.gguf`, so rename it to the name the Modelfile expects.

2. Build it:

```bash
ollama create CodeGenTutor -f models/Modelfile.codegen-tutor
```

3. Set up **Settings** as usual (Local (Ollama), `http://localhost:11434/v1`),
   then use **Custom Practice**: topic, difficulty, and the generator model name
   — `CodeGenTutor` by default.

The generator does **not** have to be the fine-tuned model. Any instruct model
will attempt it and the app checks the result either way; the fine-tune just
raises the hit rate a lot. `gpt-4o-mini` or a 70B on Groq will also work if you
would rather not train anything.

### What the app does with what the model returns

Every generated question is run through the real sandbox **before the student
sees it**: the model's own reference solution is executed against the model's own
test cases, and the question is only served if they agree. A question that fails
is regenerated once, then reported as an error. This is the check that stops a
hallucinated `"expected"` value from handing someone an unsolvable problem.

Generated questions are written to `data/generated/` for provenance and are
never added to `data/questions/` — that folder is the recommender's question pool
and the Week 13 evaluation set. They also never change your position on the
difficulty ladder: routing stays anchored to the last real question, while the
attempt itself still counts toward your pass rate.

If a question is broken in a way the sandbox can't see — description and tests
disagreeing, for instance — the **🚩 Report broken test** button under a failed
submission logs it to `data/reports.jsonl` and offers to discard it.

---

## Troubleshooting

Every error in the app has a **Technical details** expander underneath it. Open
it — it shows the exception type, the HTTP status, the request URL, and what the
server actually said. Start there.

### "Couldn't reach the model"

The server isn't running, or the URL is wrong. Check:

```bash
curl http://localhost:1234/v1/models
```

(Use `11434` for Ollama.) If that fails, the server is down. If it succeeds but
the app still can't connect, the Server URL in the sidebar doesn't match.

### "The model server replied but sent no completion"

Almost always a **Server URL missing its `/v1` suffix**. LM Studio's UI displays
its address as `http://localhost:1234`, and pasting that alone sends requests to
`/chat/completions` instead of `/v1/chat/completions` — LM Studio answers those
with HTTP 200 and an error body, which looks like success until it's parsed.

The app appends `/v1` to a bare host automatically, so this should be fixed. If
you see it anyway, your URL has a path the app left alone; make it end in `/v1`.

### 401 "Incorrect API key provided", and the Request URL is not your provider

Your key is fine; it went to the wrong server. Check the **Server URL** in the
sidebar against the table in §3 — a Groq key sent to `api.openai.com` is
rejected by OpenAI, and the message will name OpenAI's key page rather than
Groq's. The Technical details expander shows the Request URL, which is the
fastest way to spot this.

### 404 "The model `x` does not exist or you do not have access to it"

The model id is wrong for that endpoint. The app prints the endpoint's actual
model list underneath the error — pick one of those, or use the sidebar's Model
dropdown, which is populated from the same source.

Common causes: a typo (`grok` vs Groq's `llama-3.3-70b-versatile`), a retired
model id, a missing tag (`qwen2.5-coder:7b`, not `qwen2.5-coder`), or a model
your account doesn't have access to.

### The Model dropdown is empty and shows "Couldn't list models"

The caption says why:

- **"the API key was rejected (401)"** — enter the key first. Most hosted
  providers require one even to list models. Then press **Refresh model list**.
- **"this endpoint has no /models listing (404)"** — the server doesn't
  implement it. Type the model name; that always works.
- **a connection error** — the server isn't running or the URL is wrong.

### "No server URL is set for this provider"

You chose Custom (or cleared the URL) and left it blank. The app refuses to
guess rather than quietly defaulting to OpenAI.

### "The model couldn't be used: ..."

The server's own words. Usually one of:

- **"No models loaded"** — LM Studio's server is on but no model is loaded. Load
  one on the Developer tab, or `lms load <name>`.
- **"Failed to load model"** — the model can't be loaded at all. Check you
  downloaded the main GGUF (see §2) and that you have enough free RAM.
- **"model not found, try pulling it"** — Ollama doesn't have that model.
  `ollama pull <name>`, and check the tag: `qwen2.5-coder:7b` is not
  `qwen2.5-coder`.

### "The model took too long to respond"

Local models on CPU are slow — Gemma 4 E2B measured **55–100 seconds** per
grading call on a typical laptop, longer for long solutions. Options: a smaller
model, GPU offload (`lms load <name> --gpu max`), or `EVALUATOR_MODE=stub` when
you don't need real grades.

Budget for this when running test sessions: five questions per person is roughly
ten minutes of pure model wait.

### "Could not generate a working question about ..."

Custom Practice asked twice and neither attempt survived the sandbox check. The
Technical details expander says which of the two failure modes it was:

- **`not JSON` / `missing or empty fields`** — the model isn't returning the
  schema. Expected from a general chat model; use CodeGenTutor, or a stronger
  model. If CodeGenTutor does this, check `num_ctx 4096` in the Modelfile: a
  reply truncated at 2048 tokens is never valid JSON.
- **`failed: 5/6 of its own test cases passed`** — the model wrote a problem and
  then got one of its own answers wrong. Retry, or try a different topic; very
  abstract topics ("dynamic programming on trees") fail this way more often than
  concrete ones ("two pointers").

Nothing is served when this happens — you stay on the question you were on.

### Scores look wrong or oddly harsh

Different models grade differently, and the ones committed to the report were
measured on `gemma2`. Gemma 4, for instance, produces efficiency scores gemma2
never did — see `docs/recommender_design.md` §3. If you change models, say so in
any results you report.

The evaluator also grades whatever you submit, boilerplate included: a solution
wrapped in dozens of unused imports and helper classes will score badly on style
even when the algorithm is good.
