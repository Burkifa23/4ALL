# Hint Prompt Scoring Notes

Companion to `gemma_scoring_notes.md`, which did this for the grader. The hint
prompt had never been iterated and had no baseline.

Harness: `evaluator/testing/score_hints.py`. Ten real questions from
`data/questions/`, each with a submission carrying one classic bug and one
nameable missing idea, all verified to fail with a usable `failed_case_summary`
before any inference was spent. Served model was CodeGenTutor v1 q4_k_m over
llama.cpp at temperature 0.2.

The rubric is the prompt's own four rules, so a violation is a fact rather than a
matter of taste, plus a fifth check for the specific defect found:

| rule | V1 | V2 |
|---|---|---|
| no corrected code | 10/10 | 9/10 |
| under 120 words | 10/10 | 10/10 |
| cites the failing case's values | 0/10 | 1/10 |
| grounded in the student's identifiers | **0/10** | **5/10** |
| does not echo V1's own example | **0/10** | **10/10** |
| **names the right concept** (rated by hand) | **0/10** | **4/10** |

## V1 is not weak. It is a constant function.

Across ten different questions and ten different bugs, V1 returned the same eight
words every single time:

> "Consider what happens when the list is empty."

That string is the example embedded in V1's own rules —
`- Instead, name the concept or idea the student is missing (e.g. "consider what
happens when the list is empty")`. A 3B model repeats the illustration rather than
performing the instruction. It never read a line of student code in ten attempts.

This also explains the original "hints look weak in use" report completely, and it
is worth noting the failure was invisible to two of the five rules: V1 scores a
perfect 10/10 on "no corrected code" and "under 120 words", because a constant
string trivially satisfies both. **A rubric made only of easy rules would have
called V1 healthy.**

## V2 is better and still not good

Removing the example and requiring the hint be derived from the supplied code and
failing case fixes the echo entirely and grounds half the hints in the student's
own identifiers. Four of ten name the right idea: diagonals overlapping at odd
`n`, duplicates sharing a rank, `#` grouping two digits, repeated `AB`/`CD`
removal.

The other six are the honest half of this result:

- On `q_0008` and `q_0014` it asserted **"the student's code is correct"** when it
  was not. That is worse than an unhelpful hint — it tells a student to stop
  looking.
- On `q_0007` it stated the fix outright ("should return the absolute value of the
  difference"), violating a hard rule that V2 had *strengthened*.
- On `q_0012` it named order-sensitivity for an anagram problem, where order is
  precisely what does not matter.
- `cites_case` stayed at 1/10. Both prompts ask for the failing values to be
  quoted; the model ignores it.

**Shipped anyway**, in `evaluator/prompts.py` as `HINT_PROMPT_V2_SYSTEM` and wired
into `evaluator/hints.py`. Strictly better than a constant string on every axis
that means anything, with no regression worth the name (the single `no_code` loss
is one hint against V1's ten vacuous passes).

## What this does not establish

Every measurement here ran against **CodeGenTutor**, a 3B fine-tuned to emit a
single JSON object and nothing else. That is close to the worst available model
for a 120-word conceptual explanation, and it is only the serving model because
llama-server hosts one model at a time.

So the ceiling on these numbers is unknown. The next experiment is not a third
prompt — it is running V2 unchanged against a general instruct model on a second
endpoint. `evaluator/client.py` already supports any OpenAI-compatible URL and
`generate_question(model=...)` already overrides per call, so the generator/tutor
split exists in the code; only the deployment collapses it.

Do that before considering a fine-tune for the tutor voice. Training against
Code-Feedback or FixEval would teach a model to hand over working code, which is
the one thing this prompt forbids.
