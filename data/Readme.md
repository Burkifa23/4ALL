# Question Data Format — v1 (draft, confirm at Day 2 contract review)

This is the schema contract for `data/questions/*.json`. Persons 2 (AI
evaluator), 3 (recommender/ML), and 4 (Streamlit app) build against this file.
**Changing a field name after Week 10 requires team sign-off** — see the
schema change-control rule in the role guide.

Source: derived from `newfacade/LeetCodeDataset` via `data/ingest/ingest_leetcode.py`.
Reproducible: delete `data/questions/`, rerun the ingest script with the same
`--seed`, get identical output.

## Fields

| Field | Type | Meaning |
|---|---|---|
| `question_id` | `str` | Our internal ID, e.g. `"q_0001"`. Stable across regenerations for a given seed. |
| `title` | `str` | Human-readable title, e.g. `"Two Sum"`. |
| `difficulty` | `int` | `1` = Easy, `2` = Medium, `3` = Hard. (Person 3: encode as ordinal, not one-hot, since it's genuinely ordered.) |
| `topic` | `str` | Primary tag, e.g. `"Array"`. First entry of `topics`. |
| `topics` | `list[str]` | All tags from the source dataset, e.g. `["Array", "Hash Table"]`. |
| `description_md` | `str` | Full problem description, markdown-renderable, incl. examples/constraints. |
| `starter_code` | `str` | The stub shown to the student in the editor. |
| `entry_point` | `str` | Function name the sandbox calls to run the student's submission. |
| `reference_solution` | `str` | A known-correct solution (prompt + completion). Used only for the gauntlet (validating the dataset itself) — never shown to students. |
| `test_cases` | `list[{"input": ..., "expected": ...}]` | Normalized test cases. `input`/`expected` shapes vary by problem (positional args vs. dict — confirm convention with Person 4 when wiring the child runner). |
| `test_case_count` | `int` | `len(test_cases)`. Report this honestly in the final numbers — don't imply "100+" if the real count is lower for a given question. |
| `optimal_complexity` | `str \| null` | e.g. `"O(N)"`. Null until the manual labeling pass (Person 2's request, Day 4 of Week 10). |
| `source_task_id` | `str` | Original LeetCode slug, for traceability back to the source dataset. |
| `source_question_id` | `int` | Original LeetCode numeric ID. |

## Selection criteria (applied by the ingest script)

- Single free-function entry point only (class-based / design problems like
  `LRUCache` are discarded).
- `starter_code` and `reference_solution` must both be valid Python (`ast.parse`
  succeeds).
- At least 1 test case present (target: as many as the source provides;
  report actual counts, don't inflate).
- Stratified sample: target 20 Easy / 20 Medium / 10 Hard (50 total, upper end
  of the 30–50 range for safety margin).
- At least 4 distinct topics represented, for Person 3's feature space.

## Validation

Run `python data/validate_questions.py` after every ingest run, before
committing. It checks: required fields present, valid difficulty value,
parseable code, non-zero test cases, unique `question_id`s.