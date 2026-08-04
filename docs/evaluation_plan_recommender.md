# Recommender Evaluation Plan (Week 13)

Written **before** the data arrives, so the protocol can't be tuned after
seeing which answer flatters the model.

**Question.** Does the trained classifier agree with human judgement about
`reinforce` vs `level_up` more often than a reasonable if/else rule does?

Synthetic held-out numbers (`docs/recommender_design.md` §5) can't answer this:
they measure how well the tree recovers the labeling rule that generated them.
Human raters are the first ground truth that doesn't come from the simulator.

---

## 1. Data sources

| What | Where | Produced by |
|---|---|---|
| Logged decisions | `data/predictions.jsonl` | `recommend_next()` on every live call, from Week 12 Day 2 |
| Session transcripts | `data/sessions/*.json` | Person 4's test sessions |
| Sampled cases + answer key | `data/evaluation/cases.json` | `python -m recommender.evaluate --sample 15` |
| Rater sheets | `data/evaluation/ratings_<name>.csv` | one per teammate |

If `predictions.jsonl` is thin, the evaluation is thin. Check the line count
daily from Week 12 Day 2 onward — a silent logging failure discovered on Aug 11
cannot be recovered.

## 2. Human baseline protocol

1. Sample 15 real decision points from live sessions:

   ```bash
   python -m recommender.evaluate --sample 15
   ```

   This writes `data/evaluation/rating_sheet.csv` with the feature values and a
   blank `decision` column, and `cases.json` with the model's answers.
2. **`rating_sheet.csv` does not show the model's decision or confidence.** A
   rater who can see the answer is not an independent baseline. `cases.json` is
   the hidden key — nobody opens it before rating.
3. All four teammates independently fill a copy as
   `data/evaluation/ratings_<name>.csv`, choosing `reinforce` or `level_up`
   for each case. Person 3 rates as a rater, not as the model's author — no
   peeking at model outputs first.
4. Majority vote across raters = ground truth. Ties resolve to `reinforce`,
   the conservative action. Record how many cases were unanimous; low unanimity
   is itself a finding (the task may be genuinely ambiguous, which caps how
   well *any* classifier can score).

## 3. Metrics

Produced by `python -m recommender.evaluate`:

- **Model-vs-human agreement %** and **rules-baseline-vs-human agreement %**,
  on the identical 15 cases. This pairing is the headline.
- **Per-class recall** against the human label, both systems. Report these, not
  accuracy alone — a model that never says `level_up` can still look accurate
  if humans rarely say it either.
- **Rater unanimity rate**, as the ceiling on achievable agreement.
- **Three disagreement case studies**: the feature vector, the model's decision
  and confidence, the humans' vote split, and an interpretation. These carry
  more weight in the report than the percentages at n=15.

n=15 with four raters supports a direction, not a significance claim. Say so in
the write-up. Percent agreement is the metric; Cohen's kappa exists and would
correct for chance agreement, but at this sample size it adds precision the
data doesn't have.

## 4. Distribution drift check

Before computing agreement, compare real feature distributions against the
synthetic training distribution (`data/synthetic/logs_v1.csv`): `user_pass_rate`,
`attempts_on_question`, and the efficiency/style score histograms.

Real students falling outside every archetype's range — slower, more attempts,
different score profile — is the most likely explanation for any gap between
the synthetic numbers and the human-agreement numbers. Record it either way;
"no drift observed" is also a result.

## 5. If the model loses to the rules baseline

Report it. Do not retune the model after seeing the human labels — that
converts the evaluation into a training set and makes every number meaningless.

Expected first suspect is synthetic-real drift: the classifier learned a policy
calibrated to simulated students and simulated LLM scores. Diagnose against §4,
write the causal explanation, and keep the result. A negative result with a
mechanism is stronger report material than a positive one without.

## 6. Outputs for the report

- Agreement table (model / rules / unanimity) → Section 8
- Per-class recall table → Section 8
- Three disagreement case studies → Section 8
- Drift discussion → Limitations
- `decision_tree.png`, `feature_importance.png`, `comparison.md` from
  `python -m recommender.figures` → Section 6
