# Dataset Notes — newfacade/LeetCodeDataset

*Written Day 1/2 (combined), Jul 21 2026. Based on the dataset's GitHub README
(https://github.com/newfacade/LeetCodeDataset) and HF dataset card
(https://huggingface.co/datasets/newfacade/LeetCodeDataset). Row-level claims
below need a `.iloc[0]` sanity check once you load it locally — flag anything
that doesn't match.*

## How are test cases actually stored?

Two parallel representations, per row:
- `input_output` — structured test-case data (exact inner shape TBD, verify
  locally — likely `{"inputs": [...], "outputs": [...]}` in APPS/human-eval-style
  datasets, but confirm before trusting the ingest script's parser).
- `test` — an executable Python function that checks a candidate solution
  against the cases itself.

This means we don't have to build a test harness from scratch — we can lean on
`test` directly, or normalize `input_output` into our own uniform shape and run
cases ourselves for full control over `failed_case_summary` formatting. **Decision:
normalize `input_output` into our own `{"input":..., "expected":...}` list** so
the sandbox's child runner has one consistent shape to iterate over, regardless
of how any single row's `test` function is written. Keep `test` around
unused/ignored for now — don't depend on `exec`-ing dataset-provided code deep
inside your runner without reviewing it first.

## What fields exist?

Full field list (from the dataset's own docs, human-eval format):

| Field | Meaning |
|---|---|
| `task_id` | slug, e.g. `maximize-the-beauty-of-the-garden` |
| `question_id` | numeric LeetCode ID |
| `difficulty` | `Easy` / `Medium` / `Hard` |
| `tags` | list, e.g. `['Array', 'Hash Table']` — this is our `topic`/`topics` source |
| `problem_description` | full text incl. examples & constraints |
| `starter_code` | the stub students complete |
| `estimated_date` | release date (used for train/test split, not needed by us) |
| `prompt` | prefix (imports, helper classes like `ListNode`/`TreeNode`) |
| `completion` | canonical solution body (no prompt) |
| `entry_point` | function name used for evaluation |
| `test` | callable checker |
| `input_output` | test case data |
| `query` / `response` | combined prompt+description / full solution — used for LLM training, not directly needed by us |

Reference solutions exist (`prompt` + `completion`). This is your gauntlet's
foundation: every selected question's canonical solution must pass its own
tests through the real sandbox pipeline.

## Simple single-function vs. weird (class-based/multi-function)?

Not yet measured locally (needs the actual `.iloc` pass), but structurally:
some LeetCode problems are class-based (e.g. design problems like `LRUCache`,
`MedianFinder`) rather than single free functions. **Filter rule**: reject any
row whose `starter_code` contains a top-level `class` definition — keep-pile is
single-function-entry-point problems only, which matches `entry_point` being a
plain function name for the rows we want.

## Keep-pile size estimate

Total pool: 2,869 problems (train 2,641 + test 228, v0.3.1). Even a conservative
discard rate (say, half rejected as class-based/malformed/too-sparse-on-tests)
still leaves >1,000 usable problems — comfortably above the 30–50 target and
the escalation trigger (<50) in the role guide. **No escalation needed** based
on documented structure; revisit if the local run shows otherwise.

## Difficulty/topic split target

Aiming for 20 Easy / 20 Medium / 10 Hard (50 total, upper end of the 30–50
range — safer to have surplus than come up short), with a target of ≥4 distinct
topics for Person 3's features. `tags` gives us plenty of topic variety to pull
from across 2,869 problems.

## Open questions to resolve on first local run

1. Confirm the actual inner shape of `input_output` (dict with `inputs`/`outputs`
   lists? something else?) — the ingest script's `parse_test_cases()` guesses
   this; fix it against real data.
2. Confirm `tags` is a Python list after `.to_pandas()` (vs. a stringified list)
   — affects `to_question_record()`.
3. Spot-check 3–5 rows by hand: does `prompt + completion` actually execute
   cleanly and pass its own `input_output` cases?