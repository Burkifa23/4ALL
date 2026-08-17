# Person 3 contribution to the final report

Written to match the team document's structure and prose style (continuous
academic paragraphs, past tense, file paths in parentheses). Everything below
is ready to paste.

## Where each block goes

| Block | Destination in the team document | Status |
|---|---|---|
| A | **3.4 Adaptive Recommender Engine** (replaces the placeholder) | Ready |
| B | **4.3 Recommender Model Benchmarking** (replaces the placeholder) | Ready |
| C | Three figures + one table into **4.3** | Files listed |
| D | **5. Limitations** — merge with teammates' | Ready |
| E | **6. Discussion** — merge with teammates' | Ready |
| F | **References** — merge alphabetically | Ready |
| G | Corrections to text **already written** by teammates | Action needed |

---

# A — Section 3.4 Adaptive Recommender Engine

> Paste in place of "Some 12 pts Time New Roman Fonts, Double Space" under 3.4.

The adaptive recommender is the component that converts assessment into
progression. After each submission it receives the sandbox outcome, the
evaluator's scores, and the learner's session history, and returns a decision —
either to reinforce at the current level or to advance to a harder question —
together with a specific next question and a confidence value. The design
follows the mastery-learning principle that progression should be gated on
demonstrated competence rather than on completion alone (Bloom, 1968), and
targets the band immediately beyond independent performance (Vygotsky, 1978).

Nine features are supplied to the classifier (`recommender/features.py`). Four
describe the current attempt: the question's difficulty, its topic, the number
of submissions made on it including the one being judged, and whether that
submission passed. Four summarise the session: the pass rate across all
attempts, the mean efficiency and style scores across all graded attempts, and
the most recent efficiency and style scores. Topic is one-hot encoded across the
seventeen topics present in the dataset, giving twenty-five encoded columns in
total. Difficulty is used as an ordinal integer without scaling, since decision
trees split on thresholds rather than distances and are therefore invariant to
monotone transformations of their inputs (Hastie et al., 2009). Because failed
submissions are never sent to the evaluator, the score features carry forward
from the last graded attempt, and a learner with no history receives mid-scale
defaults of 0.5 for pass rate and 3 for each score, so that a new user is
assumed neither competent nor struggling. Training and serving encode through
the same function, which makes divergence between training-time and
serving-time features structurally impossible rather than a matter of review
discipline — a failure mode identified as one of the characteristic hidden costs
of production machine-learning systems (Sculley et al., 2015).

Supervised learning requires labelled targets, and no external source supplies
them for the question "what should this learner attempt next?". A pedagogical
labelling policy was therefore defined explicitly (`recommender/labeling.py`)
and used to generate the training targets. The policy advances a learner who
passes within two attempts with an efficiency score of at least four, on the
grounds that few attempts indicate the approach was held in advance rather than
reached by trial and error, and a high efficiency score indicates a sound
algorithm rather than merely a passing one. It also advances a learner who
passes with a session pass rate of at least 0.75 and an efficiency score of at
least three, which accommodates the consistent performer who happened to labour
on one question. All other outcomes, including every failure, reinforce; this is
the conservative default, since an additional question at the same level costs a
learner time whereas premature advancement costs comprehension.

Because no real learner data existed during development, the classifier was
trained on simulated trajectories (`recommender/simulate.py`). Five archetypes —
struggler, average, advanced, fast improver and inconsistent — were parameterised
with distinct pass probabilities per difficulty level, distinct score profiles,
and distinct improvement rates, and each simulated learner completed between
five and twenty questions drawn from the real question set. Score distributions
were not invented but calibrated against fifteen recorded outputs of the
deployed evaluator, which never produced an efficiency score of two or a style
score of one and whose efficiency scores were bimodal rather than
bell-shaped; scores were therefore drawn from discrete weights reflecting those
observations. Every random operation is seeded, so the dataset regenerates
identically. Training on generated data is an established response to data
scarcity, subject to the caveat that results transfer only insofar as the
generator resembles reality (Nikolenko, 2021).

The model is a decision-tree classifier (Breiman et al., 1984) implemented with
scikit-learn (Pedregosa et al., 2011) and configured with a maximum depth of
three, a minimum of twenty samples per leaf, and balanced class weights. Because
successive rows from one simulated learner share an archetype, a running pass
rate and a difficulty trajectory, an ordinary row-wise split would place
correlated observations on both sides of the boundary and inflate every metric;
whole learners were therefore held out using grouped splitting on the learner
identifier, which is the standard remedy for structured dependence (Roberts et
al., 2017; Kaufman et al., 2012). Depth was selected from a grouped
cross-validated sweep rather than assumed. At serving time
(`recommender/engine.py`) the decision is mapped to a target difficulty and then
to a concrete question, subject to guardrails: a learner who fails is offered
the same question again up to three times before being moved sideways, no
question is served twice in a session, the search widens to the nearest
difficulty if the target level is exhausted, and the engine falls back to a
hand-written rule if no trained model is present. Every decision is appended to
a prediction log for subsequent analysis.

---

# B — Section 4.3 Recommender Model Benchmarking

> Paste in place of "Some 12 pts Time New Roman Fonts, Double Space" and
> "Learning evaluation and model benchmark table" under 4.3.

The simulator produced 2,460 decision points from 200 simulated learners, split
55.1% reinforce and 44.9% advance. The classes proved closer to balanced than
anticipated because the serving policy is self-correcting: advancement raises
difficulty, which lowers the pass rate, which returns the learner to
reinforcement. Balanced class weighting was retained regardless, since the
balance is a property of this particular simulator rather than a guarantee, and
class imbalance is a well-documented source of misleadingly high accuracy (He &
Garcia, 2009). Two checks confirmed the generator behaved as specified. The
advancement rate was monotone in designed ability, rising from 14.8% for
strugglers through 40.6% for inconsistent learners, 42.5% for average learners
and 51.7% for fast improvers to 80.9% for advanced learners. Fast improvers
climbed from 30.0% advancement in the first four questions of a session to 81.9%
from the tenth question onward, confirming that the improvement mechanism
operated as intended.

Depth was selected by grouped five-fold cross-validation over the candidate
range two to eight (Figure 4.x). Macro-averaged F1 was 0.909 at depth two and
0.998 at every depth from three to eight. Depth two is therefore clearly
underfit and performance is flat thereafter; depth three was selected as the
smallest depth on the plateau, with interpretability breaking the tie, since the
ability to display and defend the complete decision procedure is a deliverable
of this project rather than an incidental property (Rudin, 2019).

The trained classifier was evaluated against a hand-written rule baseline on 631
decisions from 50 learners held out entirely from training. The baseline
advances a learner who passed on the first attempt with an efficiency score of
at least three; it was written to be reasonable rather than to be beaten, since
a comparison against a deliberately weak alternative would carry no information.

**Table 4.x**
*Classifier and rule baseline on 631 held-out decisions from 50 unseen learners*

| Metric | Decision tree | Rule baseline |
|---|---|---|
| Accuracy | 0.997 | 0.767 |
| Macro F1 | 0.997 | 0.765 |
| Recall (advance) | 1.000 | 0.785 |
| Recall (reinforce) | 0.994 | 0.753 |

*Note.* Split by learner using GroupShuffleSplit with a fixed seed; no learner
appears in both the training and evaluation sets.

These figures require careful interpretation, and reporting them without
qualification would overstate what was achieved. The labelling policy described
in Section 3.4 is a function of four quantities — whether the attempt passed,
how many attempts it required, the efficiency score, and the session pass rate —
and all four are available to the classifier as features. The learning task is
therefore close to recovering a known three-branch rule from its own inputs,
which a tree of depth three can represent almost exactly, and which also
explains why cross-validated performance is flat from depth three onward. The
result establishes that feature assembly, encoding, training and serving
faithfully reproduce the intended policy; it does not establish that the policy
itself is pedagogically sound. The margin over the rule baseline should be read
in the same way: it quantifies the divergence between two policies rather than
demonstrating the superiority of either.

Inspection of the learned tree (Figure 4.y) supports this reading. The model
splits on the most recent efficiency score at thresholds of 2.0 and 3.5, on the
session pass rate at 0.74, on whether the last attempt passed, and on the number
of attempts at 2.5 — that is, on precisely the quantities the labelling policy
uses, with thresholds recovered where the written rule places them. Permutation
importance computed on the held-out learners (Figure 4.z) concentrates entirely
on those same features (Fisher et al., 2019). Notably, all seventeen topic
indicators received zero importance and the tree never split on topic or on
question difficulty. This is reported as a finding rather than omitted: with 50
questions distributed across 17 topics, 22 of which are Array problems and 10 of
which contain a single question, topic carries no learnable signal at this
dataset size. The feature was retained in the interface so that a larger
question bank could exploit it without a schema change.

> **Optional paragraph — include only if the human-rating study is completed
> before submission.** Delete this block otherwise; do not populate it from the
> synthetic figures above, which measure a different thing.
>
> To test whether the classifier's decisions correspond to human judgement, 15
> decision points were sampled from live sessions and rated independently by all
> four team members, who saw the feature values but not the model's output.
> Majority vote served as the reference standard. The classifier agreed with the
> human majority on **[x] of 15** cases (**[x]%**) and the rule baseline on
> **[x] of 15** (**[x]%**); raters were unanimous on **[x]** cases, which bounds
> the agreement attainable by any system. Percentage agreement is reported
> rather than a chance-corrected coefficient such as Cohen's κ (Cohen, 1960),
> because at this sample size the latter would imply a precision the data do not
> support.

---

# C — Figures and table files for Section 4.3

Regenerate with `python -m recommender.figures`, then insert from
`docs/report/figures/`:

| Placeholder above | File | Suggested caption |
|---|---|---|
| Figure 4.x | `depth_sweep.png` | Grouped cross-validated macro F1 by maximum tree depth. Performance plateaus from depth three. |
| Figure 4.y | `decision_tree.png` | The trained decision tree (depth three, balanced class weights). |
| Figure 4.z | `feature_importance.png` | Permutation importance on held-out learners. All topic indicators score zero. |
| Table 4.x | `comparison.md` | Values already transcribed into Block B. |

---

# D — Contribution to Section 5 (Limitations)

> Merge with teammates' limitations. Prose paragraphs, not bullets, to match
> the document's style.

The recommender's reported performance rests on synthetic data, and this is its
principal limitation. Every figure in Section 4.3 was measured against behaviour
generated by this project, so realism depends on the archetype parameters and
the evaluator calibration described in Section 3.4, neither of which was
validated against real learners. Relatedly, the reported accuracy is close to
tautological: all four inputs to the labelling policy are available to the
classifier as features, so the result principally demonstrates that a shallow
tree can represent a three-branch rule. It validates the implementation pipeline
rather than the pedagogy, and the model can be no better than the policy that
generated its targets. The thresholds in that policy are defensible by reference
to mastery learning but were not derived empirically, and any bias they contain
is inherited in full.

The model-selection procedure was also not fully nested. The depth sweep used
grouped cross-validation across the whole dataset, including the learners later
used for evaluation, so the reported metrics are mildly optimistic with respect
to the choice of depth (Cawley & Talbot, 2010). Given that performance was flat
from depth three to depth eight, the practical effect is small, but the
procedure does not constitute clean nested cross-validation.

The most influential feature, the most recent efficiency score, originates from
a language model whose calibration set misclassified two of fifteen brute-force
solutions — specifically those whose inefficiency was concealed within a single
loop. Language models used as judges are known to exhibit systematic biases
(Zheng et al., 2023), and this noise propagates directly into the routing
decision. The calibration is moreover model-specific: the simulator was tuned to
the outputs of one local model, and a check against a different model produced
efficiency scores the original never emitted, so results are valid only for the
model actually used and the model identifier must be reported alongside them.

Finally, the topic features are inert at this dataset size and were never used
by the model, so no claim about topic-aware routing is supported by this work;
the recommender has no memory across sessions and no per-skill representation,
so it cannot express which topics a learner has mastered, which is the concern
addressed by knowledge-tracing approaches (Corbett & Anderson, 1994; Pelánek,
2017); and the confidence value should be read as an ordinal signal rather than
a probability, since decision-tree class probabilities are known to be poorly
calibrated (Niculescu-Mizil & Caruana, 2005).

---

# E — Contribution to Section 6 (Discussion)

> Merge with teammates' discussion.

The recommender demonstrates that a simple, fully interpretable classifier is
sufficient to drive adaptive progression in a system of this scale, and that the
engineering discipline surrounding such a model matters at least as much as the
model itself. Sharing a single encoding function between training and serving,
holding out whole learners rather than individual observations, and selecting
depth from a cross-validated sweep rather than by assumption were each
consequential decisions; the fact that the learned tree recovers the intended
policy's thresholds is the clearest available evidence that the pipeline
contains no feature or labelling defect.

The more instructive finding is a negative one. Because the labelling policy's
inputs are all present as features, near-perfect accuracy on held-out simulated
learners was close to guaranteed, and it would have been straightforward to
present that figure as evidence that machine learning outperforms rule-based
gating. It is not such evidence. This illustrates a general risk in applying
supervised learning to a problem whose labels are themselves generated by a
rule: the model can only recover the rule, and the apparent margin over an
alternative rule measures disagreement between two policies rather than the
merit of either. The claim the project can legitimately support is narrower than
the headline number suggests — that a learned gate reproduces an explicit
pedagogical policy faithfully and degrades gracefully on incomplete inputs — and
establishing whether that policy is pedagogically sound requires agreement with
human judgement, not further work on the classifier.

The choice of a depth-three decision tree over a more expressive model was
therefore deliberate rather than a concession. In a setting where decisions
affect learners, a model whose complete logic can be printed, read and contested
is preferable to a more opaque one of comparable accuracy (Rudin, 2019;
Doshi-Velez & Kim, 2017), and where cross-validated performance is flat across
depths there is no accuracy to trade away. The practical value the classifier
adds over executing the rule directly is correspondingly modest but real: it
consumes the incomplete and noisy feature vector the application actually holds
rather than requiring clean inputs, it produces a graded confidence signal that
a boolean cannot, and it can be retrained on real session data as that data
accumulates, whereas a hand-written rule improves only when someone rewrites it.

---

# F — References to merge

> Merge into the shared reference list, alphabetically. Verify page numbers and
> DOIs against the publisher record before submission.

Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment, 1*(2), 1–12.

Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984).
*Classification and regression trees*. Wadsworth.

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and
subsequent selection bias in performance evaluation. *Journal of Machine
Learning Research, 11*, 2079–2107.

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

---

# G — Corrections needed in text already written

These are factual errors or gaps in sections written by other team members.
Flagged rather than silently changed.

**1. The BYOM description is out of date (Abstract, §1.2, §1.3 objective 3,
§3.3).** The text says the system supports "a local Ollama/Gemma model and the
OpenAI cloud API". The implementation is no longer restricted to those two: the
provider name determines nothing, and any OpenAI-compatible endpoint works —
Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter, Together, or a
custom gateway — configured by URL, key and model name in the interface.

Suggested replacement for the §3.3 sentence: "It uses a bring-your-own-model
architecture in which the endpoint URL, credentials and model name are supplied
at runtime, so any OpenAI-compatible service — whether a locally hosted model or
a hosted API — can be substituted without code changes, allowing the trade-off
among cost, latency and privacy to be adjusted per deployment."

This matters beyond accuracy: provider-independence is the strongest support for
the accessibility argument made in §1.1 and §1.4, and the current text
understates it.

**2. Section 2 (Background) contains no citations.** The claims that "research
on adaptive formative assessment suggests..." and "recent educational tools have
combined code execution with AI-generated explanations" both require sources.
Several references in Block F above are suitable — Bloom (1968) and Vygotsky
(1978) for adaptive progression, Corbett and Anderson (1994) and Pelánek (2017)
for learner modelling, Zheng et al. (2023) for the reliability of language-model
judgements.

**3. Section 1.1 states test cases number "100+" per question.** The actual
range across the 50 selected questions is 37 to 234, with a mean of
approximately 100. If that claim appears in the final text, it should read
"typically around 100" rather than "100+".

**4. The abstract promises evaluation of "cost" and "fairness".** Neither is
currently addressed in Sections 4 or 5. Either the bias-audit and latency
results should be included, or the abstract should be narrowed to match what is
reported.
