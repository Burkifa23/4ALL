# CodeGenTutor — what the fine-tune achieved, and what it didn't

**Verdict.** The fine-tune succeeded completely at the thing a fine-tune can teach, and
did not move the thing it can't. Schema compliance went from ~0/20 to 13/20 on held-out
topics. Self-consistency — whether the model's own test cases are ones its own reference
solution actually passes — stayed at 0/20 in every measurement of every artifact.

Those are not two degrees of the same result. They are two different problems, and only
the first one was ever a formatting problem.

---

## 1. What was trained

| | |
|---|---|
| Base | `unsloth/Qwen2.5-Coder-3B-Instruct`, 4-bit |
| Method | QLoRA, `r=16`, `lora_alpha=16`, dropout 0, all seven projections |
| Data | `newfacade/LeetCodeDataset`, filtered by this repo's own ingest pipeline |
| Schedule | 2 epochs, 578 steps, effective batch 8, lr 2e-4 linear |
| Final loss | ~0.18 |
| Output | `codegen-tutor.Q4_K_M.gguf`, 1.84 GB |

Two choices in there carry the weight of the evaluation:

**The split is by held-out topic, not random.** A random 5% split would let the model
recall a problem it saw in training under the same topic label, and the number would
measure memorisation. Held-out topics measure what a student typing "Sliding Window"
actually asks for — can it write this schema for a topic nobody trained it on.

**The checkers are the app's own.** `_parse()` is literally what `app.py` calls on
CodeGenTutor's reply; the sandbox check is the one that decides whether a student gets a
solvable question. Nothing here is a proxy metric invented for the report — a question
that scores is a question the app would serve.

## 2. What was measured

Three artifacts, and they are not interchangeable:

1. **The base model**, adapters zero-initialised — the control.
2. **The adapters**, in transformers on the training GPU. This is what the notebook
   reports and what most fine-tuning write-ups would stop at.
3. **The served GGUF** — a q4_k_m quantisation of a *merge* of those adapters, over HTTP,
   through llama.cpp, at the sampling settings in `models/Modelfile.codegen-tutor`.

Only the third is what a student meets. Measuring it separately is the difference between
"the fine-tune worked" and "the thing we ship works", and they turned out to differ.

| metric (n=20) | base | adapters | served GGUF |
|---|---|---|---|
| valid JSON | 0/20 | **13/20** | 8/20 |
| all 6 fields | 0/20 | **13/20** | 8/20 |
| tests self-consistent | 0/20 | **0/20** | **0/20** |

Raw evidence: `evaluator/testing/scorecard_adapters.json`,
`evaluator/testing/scorecard_served.json`.

**One caveat on the third column.** The served run draws its topics from
`data/questions/`, while the notebook draws them from the held-out slice of
LeetCodeDataset. The request sets differ, so 8/20 and 13/20 are not a controlled
comparison — the gap is suggestive, not measured. What *is* directly comparable is that
the same three counters, on the same checkers, put self-consistency at zero everywhere.

Note also that `valid JSON` and `all 6 fields` are identical in every column. Every single
reply that parsed as JSON had all six taught fields, correctly named, with `entry_point`
agreeing with `starter_code`. The schema was not partially learned. It was learned.

---

## 3. Finding 1 — a token ceiling, found twice

The first scoring run used `max_new_tokens=1600` and returned 8/20. Raising it to 3072,
changing nothing else, returned 13/20. Five of the twelve "failures" were the ceiling.

The signature is unmistakable in the served run's log. Twelve replies were rejected as
not-JSON, and they failed at character positions 8818, 8957, 9097, 9133, 9149, 9316, 9499
— a band roughly 700 characters wide, at ~3 characters per token for JSON-with-code, which
is ~3072 tokens. That is the server's `-n`. Every one of them took 470–550 seconds; the
eight that succeeded returned in 41–219 seconds. Generations do not naturally cluster like
that. They ran into a wall.

The failure mode matters because of how it presents: a truncated JSON object fails
`json.loads` in exactly the same way a malformed one does. **A generation ceiling is
indistinguishable from "the model can't write JSON" unless you look at where the parse
died.** Both times, the metric was reporting a configuration limit as a model defect.

This is also why the served number needs its own investigation rather than a shrug — a
quantised model may terminate less reliably than the unquantised one, in which case the
ceiling bites harder on exactly the artifact that ships.

## 4. Finding 2 — the model cannot predict its own code's output

This is the real one, and no amount of further fine-tuning addresses it.

The taught schema asks the model to write `reference_solution` — working Python — and then
to state, from memory, what that code returns for each test input. Writing the code is a
coding task, and a code model is good at it. Stating the return value is *simulating a
Python interpreter in your head*, and a 3B model cannot do it.

Every correctness failure in the served run is that same act:

```
Union Find      failed: 0/8 of its own test cases passed - got 5, expected 3
Stack           failed: 6/8 of its own test cases passed - got ['rkh'], expected ...
Tree            failed: 7/8 of its own test cases passed - got 55, expected ...
Two Pointers    failed: 0/8 - raised TypeError
Math            timeout: 0/8 - Exceeded 5s time limit
```

The `6/8` and `7/8` rows are the tell. Those are not broken questions — they are questions
where the model got most of the arithmetic right and slipped on one or two cases. It is
not failing to understand the task. It is failing to compute.

A second, rarer failure sits alongside it: the problem statement itself can be incoherent.
From the notebook's sample cell, a schema-perfect record titled *Maximum Frequency Of A
Group*:

> "For a subarray of size **n**, we define its frequency..." — where `n` is never defined,
> `k` appears in the signature and constraints but does nothing in the problem, and one
> test expects `10` for a ten-element array under a rule that can only return `1`.

Perfect JSON. All six fields. `entry_point` matching `starter_code`. And a problem no
student could solve, because it doesn't describe a computable task.

## 5. What follows from this

**The fine-tune is a success, correctly scoped.** 0/20 → 13/20 on schema compliance over
held-out topics is the result, and it is the result that was available: r=16 over ~2k
examples of a formatting task teaches shape. Self-consistency was never a fine-tunable
property. Treating the 0/20 as "the fine-tune failed" would misread which of the two jobs
the training data could possibly teach.

**The fix is architectural, not more training** — and it is now in the code. The model is
no longer asked to predict `expected` at all. `sandbox.runner.solution_outputs()` runs the
model's solution against the model's test *inputs* in the same isolated subprocess and
under the same AST security check as a student submission, and
`evaluator.generate._fill_expected()` writes the real return values back into the question
before `_verify()` sees it. Self-consistency now holds by construction for every question
whose solution runs, at no training cost. `_verify()` stays where it was: it has stopped
being a coin flip and become an assertion that the harvesting worked.

Three edge cases that fix creates, all closed:

- A value that does not survive JSON unchanged — a tuple encodes fine and returns as a
  list, and `(1, 2) != [1, 2]` — would make a correct solution fail its own tests. Those
  cases are dropped, and a question with fewer than four survivors is rejected.
- A solution returning the same value for every input yields tests that are true,
  consistent, and passable by a one-line stub. The degenerate-output gate rejects those.
- A computed `None` nearly always means the solution ran off the end through a branch it
  never wrote. Those cases are dropped rather than recorded — see §6, where this cost a
  question before it was caught.

**The limitation that creates, stated plainly.** Computing `expected` by execution
guarantees a question is *solvable and self-consistent*. It does not guarantee the tests
match the prose. If the model writes a solution for a slightly different problem than the
one it described, the result is a coherent, solvable, subtly-wrong exercise. That is a
much better failure than an impossible question — a student can always finish it — but it
is a real weakening, and it leaves description/solution coherence as a human-review
problem. The gates above catch the mechanical cases; they cannot catch a description that
quietly disagrees with a working solution.

**Why this doesn't make the fine-tune redundant.** Execution fixes correctness; it does
nothing for format. A base model that emits 0/20 parseable replies has nothing for the
sandbox to run. The two halves compose: the fine-tune makes the output machine-readable,
execution makes it true.

**And it feeds back into training.** Since `expected` is computed, teaching the model to
write it is capacity spent on a solved problem — and it is most of the assistant turn, so
it is also the direct cause of Finding 1. The taught schema now carries test *inputs*
only, in `target_json()` in the notebook and in `SYSTEM_PROMPT` (which
`models/Modelfile.codegen-tutor` mirrors byte-for-byte, enforced by
`tests/test_generated_question.py`). Expect roughly 40% shorter generations from the
retrained model, which should stop the ceiling biting regardless of how the token
question resolves.

A note on the numbers after this change: `score_generator.py` now runs `_fill_expected()`
before `_verify()`, exactly as `generate_question()` does, so it measures the **pipeline**
rather than the raw model. The pre-change raw figures are preserved in
`scorecard_served.json` for comparison — that is the honest baseline for the delta.

---

## 6. The live run

Three questions generated through the Streamlit app's own Custom Practice path, against
the q4_k_m GGUF served by llama.cpp on CPU. All three passed on the **first attempt**;
under the old pipeline all three would have been rejected twice and handed the student an
error.

| | topic | wall time | title |
|---|---|---|---|
| `gen_0001` | Sliding Window | 70s | Minimum Size Subarray Sum |
| `gen_0002` | Sliding Window | 65s | — |
| `gen_0003` | Sliding Window | 168s | Sliding Window Maximum |

Because the model still writes its own answers — under an `"output"` key, having been told
not to use `"expected"` — the saved records caught it in the act. `gen_0001`, its guesses
beside the values the sandbox computed:

| input | model said | actually |
|---|---|---|
| `target=20, [1]*20` | 0 | **20** |
| `target=20, [1..20]` | 10 | **1** |
| `target=5, [2]*10` | 1 | **3** |
| `target=100, [1..50]` | 50 | **3** |

Four of eight wrong. `gen_0003` the same shape: it claimed `[3,3,5,5,6,7]` for a
seven-element input where only five windows exist. Both reference solutions are textbook
sliding-window implementations — **the code is right and the arithmetic about the code is
wrong**, which is Finding 2 in its purest form.

Then the student half, on `gen_0003`. A solution written independently of the model's —
`[max(nums[i:i + k]) for i in range(len(nums) - k + 1)]`, a different algorithm entirely —
was submitted through the editor and **passed 8/8**, with the grader returning `O(N^2)`,
efficiency 1/5, style 4/5.

That last part is the claim worth making carefully. Passing the *reference* solution would
prove nothing, since the expected values are defined by running it. Passing an
independently written one is what shows the question is genuinely **solvable**, not merely
self-consistent.

### What a fifth question caught

A request for "Two sum", difficulty Hard, returned `gen_0005` — LeetCode 167, whose eight
expected values were all exactly what its reference solution returns. Perfectly
self-consistent, and still not a servable question:

- Two cases expected `null`. The description states *"the tests are generated such that
  there is exactly one solution"* and the starter code is annotated `-> List[int]`. A
  student reading the problem correctly returns a list and fails both.
- The mechanism: the model borrowed a problem whose statement guarantees a match, wrote
  the idiomatic two-pointer solution with **no no-match branch**, then invented inputs
  with no match (`[1..5]` target 10). The implicit `None` became the specification.

That is the prose/tests gap in its most tractable form, so it is now gated: a computed
`None` is dropped as an unhandled branch. Replayed through the fixed gate, `gen_0005` keeps
six valid cases, sheds both nulls, and passes.

**One thing no gate fixes.** The request was for *Hard* and returned an *Easy* problem.

The obvious explanation is that the training data starved the model of Hard examples: the
keep-pile filter drops problems whose starter code mentions `TreeNode` or `ListNode`, and
those might plausibly skew Hard. Measured, that is **wrong**:

| | raw | kept | survival | share of keep-pile |
|---|---|---|---|---|
| Easy | 686 | 625 | 91% | 24% |
| Medium | 1498 | 1336 | 89% | 51% |
| Hard | 685 | 638 | **93%** | 25% |

Hard survives better than either other band, and the tree/list filter rejects only 1% of
Hard against 7–8% of Easy and Medium — `TreeNode`/`ListNode` problems are mostly
easy traversals, while genuinely hard ones are DP and graph work over flat arrays. The
model trained on 638 Hard examples, a quarter of everything it saw.

(The 20/20/10 split in `data/questions/` is unrelated — that is `stratified_sample()`
filling a deliberate quota for the app's question pool, not the filter's natural output.)

So this is not a data problem. `difficulty` reaches the model as one adjective in
`"Generate a {name} Python programming challenge about {topic}."`, against a topic word
that determines the entire problem domain. The model learned to condition on the strong
signal and ignore the weak one. Whether a more prominent difficulty cue in the user turn
would fix it is untested — and deliberately not being tested in v2, so that any change in
the scores can be attributed to the schema change alone.

---

## 7. v2 — the inputs-only schema

v2 changed exactly one thing: `target_json()` teaches test *inputs* only, since `expected`
is computed in the sandbox. The prediction was ~40% shorter assistant turns and therefore
fewer truncations.

**The prediction did not hold. v2 is not measurably better than v1, and the first
measurement that said otherwise was wrong.**

### The corrected comparison

Both models, n=50, identical server flags (`--jinja -c 8192 -np 1 -n 3072 -t 6`), identical
seeded request list:

| n=50, served | v1 | v2 |
|---|---|---|
| valid JSON | **33/50 (66%)** | 26/50 (52%) |
| all 6 fields | **33/50 (66%)** | 26/50 (52%) |
| tests self-consistent (pipeline) | 19/50 (38%) | 18/50 (36%) |
| wall clock | 96 min | 114 min |

The schema gap is 1.44σ and the pipeline gap is 0.21σ. Neither is significant: **the two
models are indistinguishable, with v1 nominally ahead.** v2 was also *slower*, not faster —
the opposite of the shorter-output prediction, because its remaining failures are
repetition loops that burn the full token budget.

### Why the earlier n=20 result was misleading

An interim run put v1 at 8/20 and v2 at 13/20, and that was read as v2 fixing a token
ceiling. It was an artefact of the **baseline being measured under a different server
configuration**. v1's 8/20 ran with `-c 4096`, which was throwing
`500 - Context size has been exceeded` mid-run; v2's 13/20 ran with `-c 8192`. Comparing
them was comparing two server configs, not two models. Re-measured under identical flags,
v1 scores 66%.

That also dissolves the "adapters-to-served gap" argument built on top of it: v1's adapters
scored 65% and v1 served scores 66% — there is no gap to explain. The 5-point drop
attributed to quantisation was the misconfigured context.

**The lesson is procedural and worth keeping**: every artifact in this project has now been
mis-measured at least once by a configuration difference rather than a model difference —
`max_new_tokens=1600`, then `-n 3072`, then `-c 4096`. A number is only a model result when
the two sides were produced by the same harness on the same settings.

### What survives

The retrain is not the win. **The pipeline is.** Both models convert roughly 37% of requests
into verified, solvable questions, against 0/20 raw self-consistency for either. That figure
is model-independent, which is the point: `_fill_expected()` supplies correctness that no
version of the fine-tune ever provided.

v1 remains the shipping model on this evidence — nominally better, faster, and already
proven end to end in the app.

### The failure modes, and what is actually established about them

**v2 produces repetition loops.** Solidly evidenced, and observed under the good
configuration: its rejections die at 162, 172, 186, 610, 4,026, 4,327 and 4,764 characters
with tails reading `0000000000…`, `1, 1, 1, 1, 1…`, `[0,0,0…], [0,0,0…]`, `mx + mx + mx…`.
Those are not questions cut off mid-sentence; the model is stuck emitting one fragment
until it hits the cap.

**v1's "truncation at the token wall" is now the weaker claim.** Its twelve rejections
clustered between characters 8,818 and 9,499 — but that run was the `-c 4096` one. Prompt
plus 3,072 predicted tokens sits close to that slot's ceiling, and the same run threw
`Context size has been exceeded`. The cluster is therefore better explained by the context
limit than by the model, which is consistent with v1 scoring 66% once given `-c 8192`.

**What is not measured**: whether v1 at `-c 8192` also loops. The n=50 runs were logged as
summary lines only, so the per-question tails for both arms were not captured. Re-running
either arm with the full output retained would settle whether repetition is a v2 regression
or a property of both.

That is a different defect with a different fix, and it looked like a serving-side one: a
sequence-level sampler rather than more training or more context. **Tested, and rejected.**

`--dry-multiplier 0.8`, everything else identical, same 20 topics:

| v2 served | plain | + DRY |
|---|---|---|
| valid JSON | 13/20 | **16/20** |
| tests self-consistent | **10/20** | 5/20 |
| parse → servable | 10/13 = **77%** | 5/16 = 31% |

The sampler did what it was asked — the loops stopped and schema compliance rose to 80% —
and it broke the code inside. Ten replies parsed cleanly and then failed with "the reference
solution did not run at all" or "only 0 of 8 test inputs produced a usable result".

The reason is worth recording, because the risk was anticipated in the wrong place. The
concern was that test *inputs* contain legitimate repetition (`[0,0,0,0]` is a fair edge
case). The real damage was to the *reference solution*: Python is dense with legitimate
repetition — indentation, `for i in range`, repeated identifiers — and penalising repeated
sequences yields code that no longer runs. DRY buys structural validity by destroying
semantic validity, and the conversion from "parses" to "servable" collapses from 77% to 31%.

**Plain serving is the shipping configuration.** The repetition loops remain an open defect,
and being a generation-behaviour problem rather than a decoding one, the honest next
candidate is training (or a prompt rule bounding test-input size) rather than a sampler.

**The pipeline yield is the number that matters to the app**: at n=50, 19/50 requests on v1
and 18/50 on v2 produce a verified, solvable question — roughly 37% either way, against
0/20 raw self-consistency for either model. The two gates earned their place in the same
runs: "every test case expects `False`, so a stub would pass" and "every test case expects
`0`, so a stub would pass" each caught a question that was internally consistent and
worthless.

Note that `tests self-consistent` changed meaning partway through this project and the
figures must not be read as a series. The 0/20 rows in §2 measure the **raw model**; every
figure from §7 on measures the **pipeline**, because `_fill_expected()` now runs inside the
harness. Raw self-consistency was 0/20 and was never re-tested — it stopped being a quantity
the app depends on.

---

## 8. Reproducing

The adapters and training checkpoints are mirrored at `Burkifa23/4all` on the Hub. The
Kaggle output folder is git-ignored — it is 7.7 GB and every byte of it is reproducible.

```bash
llama.exe server -m codegen-tutor_gguf/qwen2.5-coder-3b-instruct.Q4_K_M.gguf --jinja -c 8192 -np 1 -n 6144 -t 6 --port 8080
```

```bash
python -m evaluator.testing.score_generator --n 20 --out evaluator/testing/scorecard_served.json
```

`evaluator/testing/score_generator.py` re-implements none of the checks — it calls the
same `complete()`, `_parse()` and `_verify()` the app calls. It is deliberately
single-shot, unlike `generate_question()`, which retries twice with the failure fed back:
the retry is right at serving time and wrong for a measurement.
