# Report contributions — Person 3 (Adaptive Recommender)

Contains **Section 6** (complete), the recommender half of **Section 8**
(protocol complete, results pending Week 13 data), and Limitations bullets for
the shared section. Figures referenced here are produced by
`python -m recommender.figures` and written to `docs/report/figures/`.

---

# 6. The Adaptive Recommender

## 6.1 Role in the system

The recommender is what makes the platform *adaptive* rather than an autograder
with a fixed question order. After each submission it consumes the sandbox
outcome, the LLM's assessment of the code, and the student's session history,
and returns a decision — `reinforce` or `level_up` — together with a concrete
next question and a confidence value.

```
sandbox result + LLM scores + session history + question metadata
    → FeatureVector          (contracts/types.py)
    → DecisionTreeClassifier (recommender/models/decision_tree_v1.joblib)
    → Recommendation         (decision, next_question_id, confidence)
```

The design follows the mastery-learning tradition, in which progression is
gated on demonstrated competence rather than on time spent or questions
completed (Bloom, 1968), and targets the band just beyond current independent
performance (Vygotsky, 1978). It is a deliberately simple member of the learner
modelling family; richer alternatives such as knowledge tracing model per-skill
mastery over long horizons (Corbett & Anderson, 1994; Pelánek, 2017), which a
five-to-twenty question single session cannot support.

## 6.2 Feature design

`recommender/features.py` is the single source of truth for feature
definitions. Both training and serving encode through the same
`vector_to_row()` function, which makes training/serving skew structurally
impossible rather than a review checklist item — a failure mode identified as
one of the characteristic hidden costs of production ML systems (Sculley et
al., 2015).

**Table 6.1 — Feature definitions and cold-start defaults**

| Feature | Definition | Cold start |
|---|---|---|
| `question_difficulty` | 1 = Easy, 2 = Medium, 3 = Hard | — |
| `question_topic` | one-hot over 17 frozen topics; unknown → all zeros | — |
| `attempts_on_question` | submissions on this question, **including** the one just judged | 0 |
| `last_attempt_passed` | whether the submission just judged passed all tests | False |
| `user_pass_rate` | passes ÷ **attempts** across the session so far | 0.5 |
| `avg_efficiency_score` | mean LLM efficiency over all graded attempts | 3.0 |
| `avg_style_score` | mean LLM style over all graded attempts | 3.0 |
| `last_efficiency_score` | efficiency of the most recent graded attempt | 3 |
| `last_style_score` | style of the most recent graded attempt | 3 |

Total encoded width is 25 columns: 8 numeric plus 17 topic indicators.
Difficulty is used as an ordinal integer without scaling, since decision trees
split on thresholds rather than distances and are invariant to monotone
transformations of the inputs (Hastie et al., 2009).

Three definitions were ambiguous enough to pin explicitly, each a plausible
source of train/serve divergence:

1. **The current attempt is included.** The UI appends to history on submit,
   before any recommendation is requested, so `attempts_on_question` is ≥ 1 at
   every real decision point and 0 only at cold start.
2. **`user_pass_rate` is per attempt, not per question.** A student who failed
   three times then passed has a pass rate of 0.25, not 1.0.
3. **Failed attempts are never graded.** The application invokes the LLM
   evaluator only on a passing submission, so failures contribute no scores and
   the score features carry forward from the last graded attempt.

Cold-start values are mid-scale by design. Zero would make every new student
resemble a failing one and bias the first recommendation toward `reinforce`;
0.5 and 3 assume nothing.

## 6.3 Labelling policy

Supervised learning requires targets, and no external source supplies them for
"what should the next question be?". `recommender/labeling.py` therefore defines
the policy explicitly, the simulator generates data under it, and the classifier
learns to approximate it. The policy is a two-branch mastery gate:

- **Branch 1 — passed within 2 attempts and efficiency ≥ 4 → `level_up`.**
  Few attempts indicate the student held the approach in advance rather than
  converging by trial and error; a high efficiency score indicates a sound
  algorithm rather than merely a passing one. Together these constitute strong
  single-question evidence.
- **Branch 2 — passed, session pass rate ≥ 0.75 and efficiency ≥ 3 →
  `level_up`.** This captures the consistent performer who happened to labour
  on one question; a sustained record substitutes for single-shot evidence. The
  efficiency floor of 3 excludes brute force, which the evaluator reliably
  scores 1, while admitting merely competent code.
- **Otherwise → `reinforce`**, including every failure. Reinforcement is the
  conservative default: an extra question at the same level costs a student
  time, whereas premature promotion costs comprehension.

Making the policy explicit and inspectable is itself a design choice. In
decision settings that affect people, an interpretable model whose logic can be
stated and contested is preferable to a more opaque one of comparable accuracy
(Rudin, 2019; Doshi-Velez & Kim, 2017).

## 6.4 Synthetic training data

No real user data existed before Week 13, so the classifier was trained on
simulated learning trajectories (`recommender/simulate.py`, seed 42, fully
reproducible). Training on generated data is an established response to
data scarcity, with the standard caveat that results transfer only insofar as
the generator resembles reality (Nikolenko, 2021).

**Table 6.2 — Student archetypes (40 simulated students each)**

| Archetype | P(pass) Easy / Med / Hard | Efficiency profile | Improvement per question | Noise |
|---|---|---|---|---|
| Struggler | .55 / .25 / .08 | mostly 1, some 3 | +0.01 | 0.05 |
| Average | .80 / .55 / .25 | spread across 1/3/4/5 | +0.02 | 0.05 |
| Advanced | .95 / .85 / .60 | mostly 5 | +0.01 | 0.04 |
| Fast improver | .55 / .25 / .08 (starts as struggler) | struggler → advanced | +0.06 | 0.05 |
| Inconsistent | .80 / .55 / .25 | bimodal (1s and 5s) | +0.02 | 0.10 |

Sessions run 5–20 questions. Pass probability rises with cumulative progress
and carries per-question Gaussian noise; the score profile blends toward the
advanced profile at the same rate; patience (2–4 submissions before abandoning
a question) is drawn per question; difficulty starts at Easy and rises whenever
the generated label is `level_up`; questions are drawn from the real 50-question
set and never repeated within a session.

Patience is randomised deliberately. A fixed abandonment point would have made
every failure take exactly four submissions, supplying the model with an
artefactual "four attempts implies failure" signal absent from real sessions —
a small instance of the leakage-by-construction problem described by Kaufman et
al. (2012).

### 6.4.1 Calibration against the deployed evaluator

Score distributions were not invented. They mirror 15 recorded outputs from the
`gemma2` evaluator used by the platform:

```
efficiency   1:4   2:0   3:3   4:1   5:7
style        1:0   2:2   3:2   4:7   5:4
```

Two properties drove the design. First, the evaluator **never emitted an
efficiency score of 2 or a style score of 1**, so those cells were pinned to
zero probability. Second, efficiency is **bimodal** — brute force scores 1,
competent code scores 5 — rather than bell-shaped, so scores are drawn from
discrete weights rather than a rounded clipped normal, which would have produced
a mass of intermediate values the evaluator does not generate.

This calibration is model-specific, and demonstrably so. A later check against
Gemma 4 E2B served through LM Studio produced an efficiency score of 2 on
brute-force code — a value `gemma2` never produced. The consequence is recorded
in §8 and in the Limitations: if the evaluation sessions use a different model
from the one the simulator was calibrated against, the training distribution no
longer matches the serving distribution. Session transcripts record the model
identifier and endpoint precisely so this can be checked after the fact rather
than assumed.

### 6.4.2 Generated dataset

`data/synthetic/logs_v1.csv` contains **2,460 decision points from 200
simulated students**, split 55.1% `reinforce` and 44.9% `level_up`.

The classes are closer to balanced than anticipated because the serving policy
is self-correcting: promotion raises difficulty, which lowers pass rate, which
returns the student to `reinforce`. `class_weight="balanced"` was retained
regardless, since the balance is a property of this particular simulator rather
than a guarantee, and imbalance is a well-documented source of misleadingly high
accuracy (He & Garcia, 2009).

Two sanity checks confirm the generator behaves as specified:

- `level_up` rate is monotone in designed ability — struggler 14.8%, average
  42.5%, inconsistent 40.6%, fast improver 51.7%, advanced 80.9%.
- Fast improvers climb from **30.0%** `level_up` in session positions 0–3 to
  **81.9%** at position 10 and beyond, confirming the improvement mechanic
  actually operates.

## 6.5 Training methodology

The model is a `DecisionTreeClassifier` (Breiman et al., 1984) from
scikit-learn (Pedregosa et al., 2011), configured `max_depth=3`,
`min_samples_leaf=20`, `class_weight="balanced"`, `random_state=42`.

**Grouped splitting.** Rows from one simulated student are strongly correlated:
they share an archetype, a running pass rate and a difficulty trajectory. A
row-wise `train_test_split` would place question 3 of a student in training and
question 4 in test, leaking that student's ability across the boundary and
inflating every metric. `GroupShuffleSplit` and `GroupKFold` on `student_id`
hold out whole students instead, yielding 1,829 training rows and 631 test
decisions from 50 entirely unseen students. Grouping the split by the unit that
generates the dependence is the standard remedy for structured data (Roberts et
al., 2017; Kaufman et al., 2012).

**Depth selection.** Depth was chosen from a grouped cross-validated sweep
rather than assumed (Figure `depth_sweep.png`):

| `max_depth` | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| Grouped-CV macro-F1 | .909 | **.998** | .998 | .998 | .998 | .998 | .998 |

Depth 2 is clearly underfit; performance is flat from depth 3 onward. Depth 3 is
the smallest depth on the plateau, and interpretability breaks the tie — the
ability to display and defend the entire decision procedure is a deliverable of
this project, not an incidental property (Rudin, 2019).

**Encoding.** Training does not construct its own matrix from the stored
columns; it reconstructs a `FeatureVector` per row and calls the same
`vector_to_row()` used at serving time. The serialised artefact stores the
feature names alongside the estimator, and the runtime refuses to serve a model
whose columns no longer match the current definitions rather than predicting on
misaligned inputs.

## 6.6 Results on held-out synthetic students

**Table 6.3 — Classifier versus rules baseline (50 held-out students, 631 decisions)**

| Metric | Decision tree | Rules baseline |
|---|---|---|
| Accuracy | 0.997 | 0.767 |
| Macro F1 | 0.997 | 0.765 |
| `level_up` recall | 1.000 | 0.785 |
| `reinforce` recall | 0.994 | 0.753 |

**These numbers require careful interpretation, and overstating them would be a
serious error.** The labelling policy in §6.3 is a function of four quantities —
whether the attempt passed, how many attempts it took, the efficiency score, and
the session pass rate — and all four are available to the model as features.
The learning problem is therefore close to recovering a known three-branch
function from its own inputs, which a depth-3 tree can represent almost exactly.
The 0.997 measures the fidelity of the **pipeline** — that feature assembly,
encoding, training and serving faithfully reproduce the intended policy — and
not the quality of the pedagogy.

The comparison against the rules baseline must be read the same way. The
baseline is a different and deliberately reasonable rule (`level_up` if the
question was passed on the first attempt with efficiency ≥ 3), not a strawman;
but the labels were generated by the §6.3 policy, so the gap primarily
quantifies how far the two policies diverge. It does **not** establish that
either policy is pedagogically superior. Only agreement with human judgement,
reported in §8, can address that question.

**The learned tree** (Figure `decision_tree.png`):

```
last_efficiency_score ≤ 3.5
├── user_pass_rate ≤ 0.74                → reinforce
└── user_pass_rate > 0.74
    ├── last_efficiency_score ≤ 2.0      → reinforce
    └── last_efficiency_score > 2.0      → level_up
last_efficiency_score > 3.5
├── last_attempt_passed = False          → reinforce
└── last_attempt_passed = True
    ├── attempts_on_question ≤ 2.5       → level_up
    └── attempts_on_question > 2.5       → reinforce
```

The tree splits on exactly the quantities the policy uses — code quality,
outcome, persistence and track record — and the recovered thresholds (2.0 and
3.5 for efficiency, 0.74 for pass rate) sit where the written rule places them.
This correspondence is the strongest available evidence that no feature or
label defect is present; a tree splitting on unrelated columns would indicate a
bug rather than a modelling problem.

**Feature importance** (Figure `feature_importance.png`), computed by
permutation on the held-out students (Fisher et al., 2019; Molnar, 2022),
concentrates entirely on those four features. **All 17 topic indicators have
zero importance and the tree never splits on topic or on question difficulty.**
This is reported as a finding rather than suppressed: with 50 questions spread
across 17 topics — 22 of them `Array`, and 10 topics holding a single question —
topic carries no learnable signal at this dataset size. The feature is retained
in the contract so that a larger question bank could exploit it without a schema
change.

## 6.7 Runtime behaviour and guardrails

`recommend_next(vector, exclude)` loads the model once at module level,
predicts, and derives confidence from `predict_proba`. Decisions map to target
difficulty by `level_up → min(difficulty + 1, 3)` and `reinforce → unchanged`.

- **Reinforcement means retrying.** After a failure, `reinforce` returns the
  *same* question for up to three attempts before moving the student to a
  different question at the same difficulty. Serving a new question immediately
  after a failure would teach nothing, while unlimited retries would strand a
  student who cannot solve it.
- **Difficulty-only routing.** Topic is not a selection constraint, for the
  sparsity reason in §6.6; a topic-matched search would fall back on nearly
  every call. If the target difficulty is exhausted, the search widens to the
  nearest difficulty.
- **No repeats.** The just-served question and every previously served question
  are excluded.
- **Degradation, not failure.** If no trained artefact is present the engine
  falls back to the rules baseline rather than raising, so a fresh clone still
  serves questions. Setting `RECOMMENDER_MODE=baseline` forces that path, which
  supports A/B demonstration and acts as a live fallback.
- **Prediction logging.** Every call appends the feature vector, decision,
  confidence and mode to `data/predictions.jsonl`; this file constitutes the
  evaluation dataset of §8. Logging failures are suppressed, since losing a log
  line must not terminate a student's assessment.

## 6.8 Why a classifier rather than an `if`/`else` gate

The most obvious objection to this component is that the classifier learns a
rule that was written by hand, and could simply be executed directly. The
objection is largely correct and is answered on three narrower grounds.

1. **Graceful degradation.** The written rule requires clean values for
   `passed`, `attempts` and `efficiency`. The model consumes the incomplete and
   noisy vector the application actually holds — session averages, a variable
   LLM score, sometimes no score at all — and still returns a decision rather
   than failing. LLM-produced scores are themselves noisy judgements
   (Zheng et al., 2023), so tolerance of imperfect inputs is a practical
   requirement rather than a hypothetical benefit.
2. **Graded confidence.** `predict_proba` yields a continuous signal the
   interface can act on, which a boolean cannot. This is observable in
   practice: with the evaluator returning constant placeholder scores, every
   prediction was returned at confidence 1.0; once real varying scores arrived,
   the same code produced values such as 0.970. The caveat is that decision
   tree probabilities are known to be poorly calibrated in the strict sense
   (Niculescu-Mizil & Caruana, 2005), so the value is treated as an ordinal
   signal rather than a probability.
3. **Retrainability.** Once real labelled sessions exist, the policy improves by
   retraining on better data. A hand-written rule improves only by someone
   rewriting it and re-arguing the thresholds.

The honest limitation stands: given clean inputs, the model can at best match
the rule that generated its targets, and it inherits any bias in that rule
wholesale.

---

# 8. Evaluation (recommender component)

> **Status:** protocol and instrumentation complete; results pending the
> Week 13 sessions. Sections marked **[PENDING]** are filled by running
> `python -m recommender.evaluate` once rater sheets are collected. Do not
> populate them from the synthetic figures in §6.6 — they measure different
> things.

## 8.x.1 Rationale

The synthetic results in §6.6 cannot answer whether the recommender's decisions
are *good*, only whether the pipeline reproduces the policy it was trained on.
The evaluation therefore compares the classifier's decisions against **human
judgement**, which is the first ground truth in this project not derived from
the simulator, and compares the rules baseline against the same standard so the
two are measured on identical cases.

## 8.x.2 Protocol

1. **Sampling.** `python -m recommender.evaluate --sample 15` draws 15 real
   decision points from `data/predictions.jsonl` and writes a blank rating
   sheet plus a hidden answer key (`data/evaluation/cases.json`).
2. **Blinding.** The rating sheet shows the feature values only. It does not
   show the model's decision or its confidence, since a rater who can see the
   model's answer is no longer an independent baseline.
3. **Independent rating.** All four team members independently record
   `reinforce` or `level_up` for each case as
   `data/evaluation/ratings_<name>.csv`. The author of the recommender rates as
   a rater, without first inspecting model output.
4. **Ground truth.** Majority vote across raters; ties resolve to `reinforce`,
   the conservative action.
5. **Analysis.** `python -m recommender.evaluate` computes agreement for both
   systems and prints the disagreement cases.

## 8.x.3 Metrics

- **Agreement with the human majority**, for the classifier and the rules
  baseline, on identical cases. This pairing is the headline result.
- **Per-class recall** against the human label for both systems, reported
  instead of accuracy alone: a system that never selects `level_up` can appear
  accurate whenever humans also select it rarely (He & Garcia, 2009).
- **Rater unanimity**, as an estimate of the ceiling on achievable agreement.
- **Three disagreement case studies**, presenting the feature vector, the
  model's decision and confidence, the vote split, and an interpretation.

Percent agreement is the reported statistic. Cohen's κ would correct for
chance agreement (Cohen, 1960) and is conventionally interpreted against
published thresholds (Landis & Koch, 1977), but at n = 15 with four raters it
would convey a precision the sample does not support; it is noted here for
completeness rather than reported.

## 8.x.4 Results

**[PENDING — insert the output of `python -m recommender.evaluate`]**

| | Decision tree | Rules baseline |
|---|---|---|
| Agreement with human majority | *[x/15, %]* | *[x/15, %]* |
| `level_up` recall | *[%]* | *[%]* |
| `reinforce` recall | *[%]* | *[%]* |
| Raters unanimous | *[x/15, %]* | — |

## 8.x.5 Distribution shift check

**[PENDING]** Before computing agreement, real feature distributions —
`user_pass_rate`, `attempts_on_question`, and the efficiency and style
histograms — are compared against the synthetic training distribution. A gap
between the synthetic results and the human-agreement results is most plausibly
explained by shift between the generating and serving distributions
(Moreno-Torres et al., 2012).

The model identifier must be reported alongside this comparison. The simulator
was calibrated on `gemma2`; a check against Gemma 4 E2B produced efficiency
scores that `gemma2` never emitted (§6.4.1). If the sessions ran on a different
model, that is a known and expected source of shift and must be stated rather
than discovered afterwards. Session transcripts record `provider`, `model` and
`base_url` for this purpose.

"No shift observed" is equally a result and should be reported as such.

## 8.x.6 Interpretation

**[PENDING]** If the classifier underperforms the rules baseline against human
judgement, the result is reported unchanged and diagnosed. The model must not
be retuned after the human labels are seen; doing so converts the evaluation set
into a training set and invalidates every figure derived from it (Cawley &
Talbot, 2010). A negative result accompanied by a causal explanation is stronger
evidence of understanding than an unexplained positive one.

---

# Limitations (recommender contributions to the shared section)

- **Dependence on synthetic data.** Every figure in §6.6 is measured against
  behaviour generated by this project. Realism rests on the archetype
  parameters and the evaluator calibration, both documented but neither
  validated against real learners before Week 13 (Nikolenko, 2021).

- **The synthetic result is near-tautological.** All four inputs to the
  labelling policy are available as features, so the 0.997 macro-F1 chiefly
  demonstrates that a depth-3 tree can represent a three-branch rule. It
  validates the pipeline, not the pedagogy.

- **A single, unvalidated labelling policy.** The model can be no better than
  the rule generating its targets. The thresholds (2 attempts, efficiency ≥ 4,
  pass rate ≥ 0.75) are defensible by reference to mastery learning (Bloom,
  1968) but were not derived empirically, and any bias in them is inherited
  wholesale.

- **Hyperparameter selection was not nested.** The depth sweep used grouped
  cross-validation over the full dataset, including the students later used as
  the held-out set, so the reported test metrics are mildly optimistic with
  respect to the depth choice (Cawley & Talbot, 2010). Given the flat plateau
  from depth 3 to 8, the practical effect is small, but the procedure is not a
  clean nested cross-validation.

- **Inherited evaluator noise.** `last_efficiency_score` is the single most
  influential feature and originates from an LLM whose golden-set baseline
  misclassified 2 of 15 brute-force solutions, specifically those whose
  inefficiency is concealed inside a single loop. LLM judges are known to
  exhibit systematic biases (Zheng et al., 2023), and functional-correctness
  measures for generated code are similarly imperfect (Chen et al., 2021; Liu
  et al., 2023). This noise propagates directly into the routing decision.

- **Model-specific calibration.** The score distributions were tuned to
  `gemma2`. Any other model shifts the input distribution — verified against
  Gemma 4 E2B — so results are valid only for the model actually used, which
  must be reported with them.

- **Topic is inert at this scale.** With 50 questions across 17 topics, the
  topic features carry no signal and are never used. Claims about topic-aware
  routing are unsupported by this work.

- **Small human baseline.** Fifteen cases rated by four raters supports a
  direction of effect, not a confidence interval, and no chance-corrected
  agreement statistic is reported at this sample size.

- **Confidence is ordinal, not calibrated.** Decision tree class probabilities
  are known to be poorly calibrated (Niculescu-Mizil & Caruana, 2005); the
  reported confidence should be read as a ranking signal, not a probability.

- **Single-session scope.** The model has no memory across sessions and no
  per-skill representation, so it cannot express which topics a learner has
  mastered — the concern addressed by knowledge tracing approaches (Corbett &
  Anderson, 1994; Pelánek, 2017).

---

# References

*APA 7th edition. Verify page numbers and DOIs against the publisher record
before submission; entries below are given from standard bibliographic detail.*

Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment, 1*(2), 1–12.

Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984).
*Classification and regression trees*. Wadsworth.

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and
subsequent selection bias in performance evaluation. *Journal of Machine
Learning Research, 11*, 2079–2107.

Chen, M., Tworek, J., Jun, H., Yuan, Q., Pinto, H. P. de O., Kaplan, J., Edwards,
H., Burda, Y., Joseph, N., Brockman, G., Ray, A., Puri, R., Krueger, G., Petrov,
M., Khlaaf, H., Sastry, G., Mishkin, P., Chan, B., Gray, S., … Zaremba, W.
(2021). *Evaluating large language models trained on code* (arXiv:2107.03374).
arXiv. https://arxiv.org/abs/2107.03374

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational
and Psychological Measurement, 20*(1), 37–46.
https://doi.org/10.1177/001316446002000104

Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the
acquisition of procedural knowledge. *User Modeling and User-Adapted
Interaction, 4*(4), 253–278. https://doi.org/10.1007/BF01099821

Doshi-Velez, F., & Kim, B. (2017). *Towards a rigorous science of interpretable
machine learning* (arXiv:1702.08608). arXiv. https://arxiv.org/abs/1702.08608

Fisher, A., Rudin, C., & Dominici, F. (2019). All models are wrong, but many are
useful: Learning a variable's importance by studying an entire class of
prediction models simultaneously. *Journal of Machine Learning Research,
20*(177), 1–81.

Hastie, T., Tibshirani, R., & Friedman, J. (2009). *The elements of statistical
learning: Data mining, inference, and prediction* (2nd ed.). Springer.
https://doi.org/10.1007/978-0-387-84858-7

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE
Transactions on Knowledge and Data Engineering, 21*(9), 1263–1284.
https://doi.org/10.1109/TKDE.2008.239

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data
mining: Formulation, detection, and avoidance. *ACM Transactions on Knowledge
Discovery from Data, 6*(4), Article 15. https://doi.org/10.1145/2382577.2382579

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for
categorical data. *Biometrics, 33*(1), 159–174. https://doi.org/10.2307/2529310

Liu, J., Xia, C. S., Wang, Y., & Zhang, L. (2023). Is your code generated by
ChatGPT really correct? Rigorous evaluation of large language models for code
generation. In *Advances in Neural Information Processing Systems* (Vol. 36).

Molnar, C. (2022). *Interpretable machine learning: A guide for making black box
models explainable* (2nd ed.).
https://christophm.github.io/interpretable-ml-book/

Moreno-Torres, J. G., Raeder, T., Alaiz-Rodríguez, R., Chawla, N. V., & Herrera,
F. (2012). A unifying view on dataset shift in classification. *Pattern
Recognition, 45*(1), 521–530. https://doi.org/10.1016/j.patcog.2011.06.019

Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with
supervised learning. In *Proceedings of the 22nd International Conference on
Machine Learning* (pp. 625–632). https://doi.org/10.1145/1102351.1102430

Nikolenko, S. I. (2021). *Synthetic data for deep learning*. Springer.
https://doi.org/10.1007/978-3-030-75178-4

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O.,
Blondel, M., Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos,
A., Cournapeau, D., Brucher, M., Perrot, M., & Duchesnay, É. (2011).
Scikit-learn: Machine learning in Python. *Journal of Machine Learning Research,
12*, 2825–2830.

Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond: An
overview of learner modeling techniques. *User Modeling and User-Adapted
Interaction, 27*(3), 313–350. https://doi.org/10.1007/s11257-017-9193-2

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J.,
Guillera-Arroita, G., Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B.,
Thuiller, W., Warton, D. I., Wintle, B. A., Hartig, F., & Dormann, C. F. (2017).
Cross-validation strategies for data with temporal, spatial, hierarchical, or
phylogenetic structure. *Ecography, 40*(8), 913–929.
https://doi.org/10.1111/ecog.02881

Rudin, C. (2019). Stop explaining black box machine learning models for high
stakes decisions and use interpretable models instead. *Nature Machine
Intelligence, 1*(5), 206–215. https://doi.org/10.1038/s42256-019-0048-x

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D.,
Chaudhary, V., Young, M., Crespo, J.-F., & Dennison, D. (2015). Hidden technical
debt in machine learning systems. In *Advances in Neural Information Processing
Systems* (Vol. 28, pp. 2503–2511).

Vygotsky, L. S. (1978). *Mind in society: The development of higher
psychological processes*. Harvard University Press.

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z.,
Li, Z., Li, D., Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023).
Judging LLM-as-a-judge with MT-Bench and Chatbot Arena. In *Advances in Neural
Information Processing Systems* (Vol. 36).
