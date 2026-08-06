# recommender — adaptive question selection (Person 3)

Decides `reinforce` or `level_up` after each submission and picks the next
question. Design rationale, results and limitations live in
[`docs/recommender_design.md`](../docs/recommender_design.md).

## Reproduce the model in three commands

```bash
python -m recommender.simulate
```

```bash
python -m recommender.train
```

```bash
python tests/test_recommender.py
```

`simulate` writes `data/synthetic/logs_v1.csv` (2,460 rows, 200 students),
`train` writes `recommender/models/decision_tree_v1.joblib` and prints the
classification report, and the test script exercises labeling, encoding,
feature assembly and the runtime guardrails. Everything is seeded — running
`train` twice produces an identical model.

The app-level acceptance tests run the real `app.py` headlessly:

```bash
python tests/test_app_integration.py
```

Report figures and the ML-vs-rules comparison table:

```bash
python -m recommender.figures
```

Requires `data/questions/*.json` (Person 1's set, gitignored — run the ingest
first) and the deps in `requirements.txt`.

## Using it from the app

Already wired in `app.py`:

```python
from recommender import assemble_features, recommend_next

vector = assemble_features(st.session_state.history, question)
rec = recommend_next(vector, exclude=st.session_state.served)

rec.next_question_id  # str
rec.decision          # "reinforce" | "level_up"
rec.confidence        # float 0-1
```

`assemble_features` is pure — no streamlit, no `session_state` — and is the
same function training and the tests agree with. Calling it is what guarantees
runtime features match training features.

**Call order matters.** Record the attempt (including its `LLMEvaluation`)
before assembling features: every feature is defined as including the attempt
just judged. Grade first, then `add_attempt(..., evaluation=evaluation)`, then
`assemble_features`.

History entries need `question_id` and `result` (`"passed"` counts as a pass).
`efficiency_score` and `style_score` come from the attempt's `LLMEvaluation`;
failures carry `None` for both, since only passing submissions get graded, and
the four score features then fall back to cold-start values.

Set `RECOMMENDER_MODE=baseline` to force the non-ML rules path — for A/B demos
or as a live fallback. With no trained model on disk the engine falls back to
the same path rather than raising.

## Layout

| File | What |
|---|---|
| `features.py` | Feature definitions, cold-start defaults, `vector_to_row`, `assemble_features`. The only place feature math lives. |
| `labeling.py` | The pedagogical rule that generates training targets, with its justification. |
| `simulate.py` | Seeded synthetic student generator, calibrated against Person 2's real gemma2 outputs. |
| `train.py` | Grouped-split training + depth sweep → `models/decision_tree_v1.joblib`. |
| `engine.py` | Runtime: `recommend_next`, `rules_baseline`, question index, guardrails, prediction logging. |
| `figures.py` | Report figures + model-vs-rules comparison table. |
| `evaluate.py` | Week 13 human-baseline sampling and agreement analysis. |

## Model card — `decision_tree_v1.joblib`

- Trained on `data/synthetic/logs_v1.csv` (2,460 rows / 200 students, seed 42)
- `DecisionTreeClassifier(max_depth=3, min_samples_leaf=20, class_weight="balanced", random_state=42)`
- Held out 50 whole students (`GroupShuffleSplit`, 631 decisions)
- accuracy 0.997 · macro-F1 0.997 · level_up recall 1.000 · reinforce recall 0.994
- Rules baseline on the same split: accuracy 0.767 · macro-F1 0.765
- The bundle stores `feature_names`; `engine.py` refuses to serve if they no
  longer match `features.FEATURE_NAMES`, so a feature change fails loudly
  instead of predicting on misaligned columns.

Read §5 of the design doc before quoting these numbers — they measure recovery
of the labeling policy on synthetic students, not real-world quality.
