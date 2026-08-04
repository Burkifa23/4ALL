# Recommender Design (Person 3)

The adaptive component. Takes the LLM's scores plus the student's session
history, decides `reinforce` or `level_up`, and picks the concrete next
question.

```
LLM scores + session history + question metadata
  -> FeatureVector           (contracts/types.py, assembled by recommender.features)
  -> DecisionTreeClassifier  (recommender/models/decision_tree_v1.joblib)
  -> Recommendation          (decision, confidence, next_question_id)
```

---

## 1. Features

`recommender/features.py` is the only place feature math lives. Training and
serving both encode through `vector_to_row()`, which makes train/serve skew
structurally impossible rather than a thing to remember to check.

| Feature | Definition | Cold-start default |
|---|---|---|
| `question_difficulty` | 1/2/3 from question metadata. Used raw — a tree splits on thresholds, so the Easy<Med<Hard ordering survives without an encoder | n/a |
| `question_topic` | one-hot over 17 frozen topics; unknown topic → all-zeros | n/a |
| `attempts_on_question` | submissions on **this** question this session, **including the one just judged** | 0 |
| `user_pass_rate` | passes / **attempts** (not questions) over the whole session, including the attempt just judged | 0.5 |
| `avg_efficiency_score` | mean LLM efficiency over every **graded** attempt this session (session-wide, not last-N) | 3.0 |
| `avg_style_score` | same, for style | 3.0 |
| `last_efficiency_score` | efficiency of the most recent graded attempt | 3 |
| `last_style_score` | style of the most recent graded attempt | 3 |

Three definitions were ambiguous enough to be worth pinning explicitly, because
each is a classic train/serve skew bug:

1. **The current attempt is included.** `ui/history.py::add_attempt` fires on
   submit, before any recommendation is requested, so history already contains
   the attempt being judged. `attempts_on_question` is therefore ≥1 at every
   real decision point and 0 only at cold start.
2. **`user_pass_rate` is per attempt, not per question.** A student who failed
   three times then passed has a pass rate of 0.25, not 1.0.
3. **Failed attempts are never graded.** `app.py` only calls
   `evaluate_complexity()` on a passing submission, so failures contribute no
   LLM score and the score features carry over from the last graded attempt.
   The simulator reproduces this.

Cold-start values are mid-scale on purpose. 0.0 would make every new student
look like a failing one and bias the very first recommendation toward
`reinforce`; 0.5 and 3 assume nothing.

## 2. Labeling rule

Supervised learning needs targets and nobody supplies them, so
`recommender/labeling.py` defines the policy. A mastery gate with two branches:

- **passed within 2 attempts AND efficiency ≥ 4** → `level_up`. Few attempts
  means the student had the approach up front rather than converging by trial
  and error; high efficiency means they reached a good algorithm, not merely a
  passing one. Together that is strong single-question evidence.
- **passed AND session pass rate ≥ 0.75 AND efficiency ≥ 3** → `level_up`.
  Catches the steady performer this one question happened to be slow on. A
  sustained track record substitutes for the single-shot evidence above.
  Efficiency ≥ 3 is a floor that excludes brute force (Person 2's evaluator
  scores that a 1) while accepting merely decent code.
- **everything else, including every failure** → `reinforce`. The safe default:
  another question at the same level costs a student time, promoting too early
  costs them the thread.

### "Isn't this just if/else with extra steps?"

Fair question, and the honest answer is that the classifier learns *this*
policy. What it adds over calling `label()` at runtime:

1. **Degradation instead of cliff-edges.** `label()` needs clean `passed` /
   `attempts` / `efficiency` values. The model consumes the noisy, partial
   vector the app actually has — session averages, a jittery LLM score,
   sometimes no score at all — and still returns a decision.
2. **Confidence.** `predict_proba` gives a graded signal the UI can act on
   (hold difficulty when the model is 51% sure). A boolean cannot.
3. **Retrainability.** With real labelled sessions the policy improves by
   retraining. A hand-written rule improves only by somebody rewriting it and
   re-arguing the thresholds.

The limitation is real and belongs in Limitations: with clean inputs the model
can at best match the rule, and any bias in the rule is inherited wholesale.

## 3. Simulation model

No real user data exists until Week 13, so the classifier trains on simulated
trajectories (`recommender/simulate.py`, seed 42, fully reproducible).

Five archetypes, 40 students each, 8–20 questions per session:

| Archetype | P(pass) Easy/Med/Hard | Efficiency profile | Improvement/question | Jitter |
|---|---|---|---|---|
| struggler | .55 / .25 / .08 | mostly 1, some 3 | +0.01 | 0.05 |
| average | .80 / .55 / .25 | spread across 1/3/4/5 | +0.02 | 0.05 |
| advanced | .95 / .85 / .60 | mostly 5 | +0.01 | 0.04 |
| fast improver | .55 / .25 / .08 (starts as struggler) | struggler → advanced | +0.06 | 0.05 |
| inconsistent | .80 / .55 / .25 | bimodal (1s and 5s) | +0.02 | 0.10 |

Mechanics: pass probability rises with improvement × questions completed and
carries per-question Gaussian jitter; the score profile blends toward the
advanced profile at the same rate; patience (2–4 submissions before giving up)
is drawn per question; difficulty starts at Easy and rises whenever the
generated label is `level_up`; questions come from Person 1's real 50-question
set, never repeated within a session.

**Patience varies deliberately.** A fixed give-up point would have made every
failure take exactly 4 submissions, handing the model a fake
"attempts == 4 ⇒ failed" tell that no real session contains.

### Calibration against the real evaluator

Score distributions are not invented. They mirror the 15 real gemma2 outputs in
`evaluator/testing/sample_evaluations.json`:

```
efficiency   1:4   2:0   3:3   4:1   5:7
style        1:0   2:2   3:2   4:7   5:4
```

Two findings drove the design:

- **gemma2 never emits efficiency 2, and never emits style 1.** Those cells are
  pinned to zero probability in every archetype.
- **Efficiency is bimodal, not bell-shaped** — brute force scores 1, anything
  decent scores 5. Scores are therefore drawn with `np.random.choice` over
  discrete 1–5 weights, not a rounded clipped normal, which would have produced
  a mass of 2s and 3s the real evaluator never gives.

`docs/day5_baseline.md` also notes the evaluator's blind spot: it misjudges
brute-force code whose inefficiency is hidden *inside* a single loop. That is
label noise the model inherits, and it is named in Limitations.

### Generated dataset

`data/synthetic/logs_v1.csv` — 2,519 rows from 200 students.

| | share |
|---|---|
| `reinforce` | 53.4% |
| `level_up` | 46.6% |

The classes came out near-balanced rather than the heavy `reinforce` skew
anticipated, because the serving policy is self-correcting: levelling a student
up raises difficulty, which lowers their pass rate, which pushes them back to
`reinforce`. `class_weight="balanced"` is kept anyway — it costs nothing and the
balance is a property of this simulator, not a guarantee.

Sanity checks (printed by `python -m recommender.simulate`):

- level_up rate by archetype: struggler 17.3% → advanced 85.4%, monotone in
  designed ability.
- fast improvers climb from 23.8% level_up in session positions 0–3 to 88.5% at
  position 10+, confirming the improvement mechanic actually fires.

## 4. Training

`recommender/train.py`. `DecisionTreeClassifier(max_depth=3, min_samples_leaf=20,
class_weight="balanced", random_state=42)`.

**Grouped splits, not row splits.** Rows from one simulated student share an
archetype, a running pass rate and a difficulty trajectory. A plain
`train_test_split` would put question 3 of a student in train and question 4 in
test, leaking ability into the test set and inflating every number.
`GroupShuffleSplit` / `GroupKFold` on `student_id` hold out whole students —
50 students / 667 decisions in the test set.

**Depth chosen from a sweep, not guessed.** Grouped-CV macro-F1:

| depth | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| macro-F1 | .912 | **.951** | .952 | .957 | .953 | .951 | .949 |

Depth 2 is clearly underfit; 3 onward is a plateau where the differences are
fold noise. Depth 3 is the smallest depth on the plateau, and interpretability
breaks the tie — being able to show and defend the whole tree is a deliverable
here.

The saved artifact is a bundle, not a bare estimator: it carries
`feature_names`, the training data path, and its own metrics, so `engine.py`
refuses to serve a model whose columns no longer match `FEATURE_NAMES` instead
of silently predicting on misaligned inputs.

## 5. Results (synthetic held-out students)

| metric | decision tree | rules baseline |
|---|---|---|
| accuracy | 0.963 | 0.822 |
| macro F1 | 0.962 | 0.817 |
| level_up recall | 0.997 | 0.761 |
| reinforce recall | 0.937 | 0.868 |

**Read this honestly.** The tree is not beating the baseline because trees are
magic; it wins because it sees seven features while the baseline reads two, and
because the labels were generated by a rule whose inputs are mostly features.
On synthetic data the ceiling is "recover the labeling policy", and the tree
nearly does. The claim this table supports is narrow: *given these features, a
learned gate reproduces the intended pedagogy far more faithfully than a
two-field rule.* Whether that transfers is a Week 13 question, answered against
human raters, not against the simulator.

The learned tree:

```
last_efficiency_score <= 3.50
├── user_pass_rate <= 0.74            -> reinforce
└── user_pass_rate >  0.74
    ├── last_efficiency_score <= 2.00 -> reinforce
    └── last_efficiency_score >  2.00 -> level_up
last_efficiency_score >  3.50
├── attempts_on_question <= 2.50      -> level_up
└── attempts_on_question >  2.50      -> reinforce
```

It splits on exactly the three quantities the labeling rule uses — code quality,
track record, and persistence — and **never splits on topic or difficulty**.
All 17 topic columns have zero importance. That is the expected result and is
reported as a finding, not hidden: with 50 questions across 17 topics (22 of
them `Array`, 10 topics with a single question), topic carries no learnable
signal at this dataset size. It stays in the contract so a larger question bank
can make use of it without a schema change.

Figures: `docs/report/figures/` — `decision_tree.png`, `feature_importance.png`,
`depth_sweep.png`, `comparison.md`.

## 6. Runtime behaviour

`recommender/engine.py`, entry point `recommend_next(vector, exclude=())`.

- **Routing is difficulty-only.** `level_up` → `min(difficulty+1, 3)`,
  `reinforce` → same difficulty. Topic is not a selection constraint: with 10
  of 17 topics holding a single question, a topic-matched search would fall
  back on nearly every call, so the fallback ladder is difficulty-only.
- **Guardrails.** The just-served question is always excluded; `exclude` skips
  anything Person 4 has already served; if the target difficulty is exhausted
  the search widens to the nearest difficulty; if every question is used up it
  returns the current question with confidence 0.0 rather than `None`.
- **Missing model ⇒ rules baseline, not a crash.** A fresh clone without a
  trained `.joblib` still serves questions.
- **Baseline mode.** `RECOMMENDER_MODE=baseline` forces the rules path for A/B
  demos and as the emergency fallback.
- **Prediction logging.** Every call appends the vector, decision, confidence
  and mode to `data/predictions.jsonl`. That file **is** the Week 13 evaluation
  dataset. Logging failures are swallowed — a full disk must not end someone's
  assessment.

## 7. Integration status (for Person 4)

`recommender.assemble_features(history, question)` is the runtime entry point:
pure, no streamlit, no `session_state`. It is the same function the tests and
the simulator agree with, so calling it is what guarantees parity.

One gap remains on the app side: `ui/history.py::add_attempt` records only
`(question_id, result, tests_passed, tests_total)`. Until it also records the
`LLMEvaluation` scores per attempt, `assemble_features` will fall back to
cold-start values for the four score features. It handles both shapes, so the
app works before and after that change — it just gets a sharper signal after.

`tests/test_recommender.py::test_assemble_features_canned_history` is the
parity artifact: one canned history asserted field by field.

## 8. Limitations

- **Synthetic-data dependency.** Every number in section 5 is measured against
  behaviour this repo invented. Realism rests on the archetype parameters and
  the gemma2 calibration, both documented above and both unvalidated against
  real students until Week 13.
- **Single labeling policy.** The model can only be as good as the rule that
  generated its targets. The two thresholds (2 attempts, efficiency 4) are
  defensible but not empirically derived.
- **Inherited evaluator noise.** The efficiency score is Person 2's LLM output,
  which `docs/day5_baseline.md` shows misjudges brute-force code hidden inside
  a single loop (2/15 on the golden set). Those errors propagate into the
  model's most important feature.
- **Topic is dead weight at this scale.** 50 questions across 17 topics is too
  sparse for topic to carry signal; the feature is retained for a larger bank.
- **Small human baseline.** Week 13's ground truth is ~15 submissions rated by
  four people — enough for a direction, not for a confidence interval.
