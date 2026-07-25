# Dataset Notes — newfacade/LeetCodeDataset

*Written Day 1/2, Jul 21 2026. Updated Jul 25 2026 after full local
ingestion, validation, and reference-solution verification against
2,869 real rows. All "TBD"/guessed items from the original draft are
now resolved — see "Findings from the live run" below for what actually
turned out to be true vs. assumed.*

## How are test cases actually stored?

Two parallel representations, per row:
- `input_output` — structured test-case data.
- `test` — an executable Python function that checks a candidate solution
  against the cases itself.

**Decision (confirmed correct):** normalize `input_output` into our own
`{"input": {...}, "expected": ...}` list so the sandbox's child runner has
one consistent shape to iterate over. `test` is kept around unused —
don't `exec` dataset-provided code deep inside the runner without review.

**What we actually found**, once loaded via `.to_pandas()`:
- `input_output` is a **numpy array of dicts**, not a JSON string and not
  a plain Python list. Each dict has `'input'` and `'output'` as string
  values that need their own parse pass (e.g.
  `{'input': 'nums = [3,3], target = 6', 'output': '[0, 1]'}`).
- The array itself has no commas between dict entries when printed
  (numpy's repr style), which is a display quirk, not a shape you need
  to string-patch — accessing the real array via `.tolist()` sidesteps
  it entirely.
- Each `input` string parses cleanly as keyword arguments (`nums = [3,3],
  target = 6`) via `ast.parse(f"f({input_str})", mode="eval")` and
  reading the resulting AST's keywords — safer than `eval()`.
- Each `output` string is usually a valid Python literal (`'[0, 1]'`,
  `'None'`), **but not always** — see "Known gotchas" below.

## What fields exist?

Confirmed against real rows (matches original doc-based list, no
surprises here):

| Field | Meaning |
|---|---|
| `task_id` | slug, e.g. `two-sum` |
| `question_id` | numeric LeetCode ID |
| `difficulty` | `Easy` / `Medium` / `Hard` |
| `tags` | our `topic`/`topics` source — see gotcha below on its real type |
| `problem_description` | full text incl. examples & constraints |
| `starter_code` | the stub students complete — **intentionally incomplete**, see gotcha |
| `estimated_date` | release date, unused |
| `prompt` | prefix (imports, helper classes like `ListNode`/`TreeNode`) |
| `completion` | canonical solution body (no prompt) |
| `entry_point` | e.g. `"Solution().twoSum"` — an expression, not a bare name; needs `eval()` against the exec'd namespace |
| `test` | callable checker, unused |
| `input_output` | test case data — see shape notes above |
| `query` / `response` | LLM-training fields, unused |

Reference solutions (`prompt` + `completion`) were spot-checked: all 50
sampled questions' reference solutions execute and pass their own
`test_cases`, verified via `verify_solutions.py`.

## Simple single-function vs. weird (class-based/multi-function)?

**Original filter rule was wrong.** The first draft rejected any row
whose `starter_code` contained a `class` definition — but nearly every
LeetCode row wraps its solution in a standard `class Solution:` block,
so that rule would have rejected almost the entire dataset. **Corrected
rule:** count method definitions inside the starter code; only reject
rows where the class defines **more than one** method (the real signal
for multi-method design problems like `LRUCache`).

## Keep-pile size and exclusion criteria (post-filtering, confirmed)

Total pool: 2,869 problems. **After all filters: 2,599 kept, 270
discarded.** Well above the 30–50 target — no escalation needed.

A row is dropped if any of these hold:

| Check | What it catches | Rows excluded |
|---|---|---|
| Multi-method class detection | Design problems (`LRUCache`, etc.) | (included in totals below) |
| `has_usable_tests` | No usable `input_output`, unparseable code | ~19 in first pass |
| `uses_tree_or_list_structure` | Needs `TreeNode`/`ListNode` object-graph reconstruction our flat schema can't represent | ~171 |
| `uses_external_library` | Reference solution imports non-stdlib packages (e.g. `sortedcontainers`) the sandbox won't have | ~80 |

(Exact per-filter breakdown wasn't logged separately per run — if this
matters later, worth adding a per-filter count to the script's stderr
output rather than only the final combined number.)

## Difficulty/topic split target

20 Easy / 20 Medium / 10 Hard (50 total), ≥4 distinct topics for Person
3's features. **Confirmed working** on the final run — topic-coverage
warning cleared once the coverage check itself was fixed (see gotcha
below).

## Known gotchas (resolved during live debugging — don't relitigate these)

- **`tags` and `input_output` are numpy arrays after `.to_pandas()`**,
  not strings or Python lists. Any `if not x` or `x in (...)` on them
  raises `ValueError: truth value of an array...`. Fix: check
  `hasattr(x, "tolist")` and convert before any truthiness/membership
  check.
- **String-returning problems store an unquoted bare word** as `output`
  (e.g. `leetcode`, not `'leetcode'`). `ast.literal_eval` fails on this;
  falls back to treating it as a raw string in `_parse_expected`.
- **Some `input_output` entries capture an execution error or timeout**
  instead of a real answer (`"Error: list index out of range"`,
  `"Execution timed out"`) — these come from broken auto-generated test
  cases in the source dataset. Filtered out entirely in
  `parse_test_cases`; there's no sound way to grade against "should
  raise this exact error."
- **Return-type ambiguity**: `ast.literal_eval` can't tell "the answer is
  the string `'0'`" from "the answer is the integer `0`", and can't
  parse JSON-style lowercase `true`/`false` at all. Resolved by reading
  the function's `->` return-type hint from `starter_code`
  (`_return_type_hint`) and branching in `_parse_expected` accordingly.
- **`starter_code` is intentionally incomplete** (empty function body —
  that's the point of a template). Checking it with a bare `ast.parse()`
  fails almost universally; both the ingest script and the validator
  append a synthetic `pass` at one indent level deeper before checking
  for genuine syntax errors.
- **The topic-coverage check originally read raw `tags` values directly**
  (`isinstance(tags, list)`), which is never true for a numpy array — it
  silently always reported 0 topics regardless of the actual sample.
  Fixed by routing through the same `parse_tags()` helper used
  everywhere else.

## Follow-up work (not in v1)

- **Tree/linked-list support**: would recover a meaningful chunk of the
  270 currently-excluded rows. Needs an `arg_types` field in the schema
  (e.g. `{"root": "TreeNode"}`) so the sandbox runner can invoke
  `tree_node()`/`list_node()` conversion helpers before calling the
  candidate, and a structural comparison (not `==`) on output.
- **Third-party import allowlist**: currently stdlib-only
  (`_ALLOWED_IMPORTS`); revisit if the sandbox environment later ships
  more packages by default.
- Consider logging a per-filter exclusion count (not just the combined
  total) so future re-runs can see which filter is doing the most
  rejecting if the source dataset changes.

## Verification performed before this data was committed

1. `python ingest_leetcode.py --out ../questions` — clean run, no
   warnings, 2599/2869 kept, 50 files written.
2. `python validates_questions.py --dir ../questions` — 0 errors across
   all 50 files (schema-level: required fields, difficulty range,
   parseable code, non-empty test cases, unique IDs).
3. `python verify_solutions.py --dir ../questions` — 0 failures; every
   reference solution actually executes and passes its own test cases
   (correctness-level, not just shape-level).