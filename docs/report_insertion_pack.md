# Final report — merged insertion pack

Covers two contributions that were drafted independently and collide in four places:
the **adaptive recommender** (Person 3) and the **fine-tuned question generator**.

Apply this in **one pass**, in the order given. Applying the two original packs separately
will cause the second editor to overwrite the first in the Abstract and §1.3.

Person 3's prose is carried **verbatim**. Reconciling structure was in scope; rewriting a
teammate's writing was not.

---

## Final section scheme

The brief requires an *Ethical Considerations* section and a *Conclusion*; the document
currently has neither. Adding them moves Discussion from 6 to 7.

> 1 Introduction · 2 Background · 3 Methods · 4 Results · 5 Limitations ·
> **6 Ethical Considerations** *(new)* · 7 Discussion *(was 6)* · **8 Conclusion** *(new)* ·
> References · **Appendix A: AI Use Declaration** *(new)*

**Person 3's Block E was written for "Section 6 (Discussion)". Its destination is now 7.**
No other section number changes, and no cross-reference inside either pack's prose needs
editing — all of them point at 3.x and 4.x, which are unaffected.

---

## Part A — Destination table

| # | Block | Destination | Source |
|---|---|---|---|
| 1 | Combined Abstract sentence | Abstract | **B.1** |
| 2 | Combined 1.2 paragraph | 1.2 Proposed solution | **B.2** |
| 3 | Combined 1.3 objectives | 1.3 Aim and objectives | **B.3** |
| 4 | Background paragraphs | 2. Background | **B.4** |
| 5 | Adaptive Recommender Engine | 3.4 *(replaces placeholder)* | **C.1** — Person 3 |
| 6 | Fine-Tuned Question Generation | 3.5 *(new)* | **C.2** |
| 7 | Recommender Model Benchmarking | 4.3 *(replaces placeholder)* | **C.3** — Person 3 |
| 8 | Figures 4.x / 4.y / 4.z + Table 4.x | inside 4.3 | **C.4** |
| 9 | Question-Generator Evaluation | 4.4 *(new)* | **C.5** |
| 10 | Limitations — recommender | 5 | **C.6** — Person 3 |
| 11 | Limitations — generator | 5 | **C.7** |
| 12 | Ethical Considerations | 6 *(new)* | **C.8** |
| 13 | Discussion — recommender | 7 *(was 6)* | **C.9** — Person 3 |
| 14 | Conclusion | 8 *(new)* | **C.10** |
| 15 | Merged reference list | References | **D** |
| 16 | AI Use Declaration | Appendix A *(new)* | **C.11** |
| 17 | Corrections to existing text | various | **E** |

---

## Part B — Combined replacements for shared text

These three blocks are where the two packs collided. Each is a **single replacement**
carrying both sets of changes. Do not also apply the corresponding blocks from the two
original packs.

### B.1 — Abstract

Insert after *"...recommends a subsequent question at an appropriate difficulty level."*:

The platform also includes a fine-tuned question generator, produced by adapting a 3-billion-parameter code model so that it writes new practice questions in the platform's own schema, with the expected outputs of every test case computed by executing the model's solution in the sandbox rather than predicted by the model.

*Note on the BYOM wording:* the abstract's existing phrasing ("local or cloud-based language
models", "a flexible AI wrapper that supports different model endpoints") is already
provider-neutral and does **not** need Person 3's correction. That correction is needed in
§3.3 and §1.3 objective 3 — see **E.1**.

*Also see* **E.4**: the abstract promises evaluation of "cost" and "fairness". Fairness is
now delivered by section 6. Cost is still not reported anywhere.

### B.2 — 1.2 Proposed solution

Add as a new final paragraph:

> Finally, 4ALL allows a student to request practice on a topic the fixed question bank does not cover. A language model fine-tuned for this purpose writes a new question in the same schema used by the stored questions, so that a generated question passes through the same sandbox, evaluator and recommender as any other. Because a small model cannot reliably determine what its own code returns, the expected output of each test case is obtained by executing the model's reference solution inside the sandbox, and any generated question whose tests cannot be established in this way is discarded before a student sees it.

### B.3 — 1.3 Aim and objectives

**Replace objective 3** (currently *"Design a flexible AI wrapper that can connect to either
local or cloud-based language-model endpoints."*) with:

> - Design a bring-your-own-model architecture in which any OpenAI-compatible endpoint locally hosted or remote can be configured at runtime without code changes.

**Insert a new objective** between the existing bullets 4 and 5 (after *"Generate debugging
hints…"*, before *"Train and integrate a decision-tree classifier…"*):

> - Fine-tune a small, locally deployable language model to generate new practice questions in the platform's question schema, and establish their test cases by execution rather than by model prediction.

### B.4 — 2. Background

Add after the paragraph ending *"...time complexity, or coding style."*:

A related problem is the generation, rather than the assessment, of practice material. General-purpose language models can be prompted to write programming questions, but an assessment platform requires more than readable prose: it requires a machine-readable record whose fields the sandbox, validator and recommender can all consume. Parameter-efficient fine-tuning methods such as Low-Rank Adaptation (Hu et al., 2021) and its quantised variant QLoRA (Dettmers et al., 2023) make it feasible to adapt a model to a fixed output format on modest hardware, by training a small number of additional parameters while the original weights remain frozen and quantised. This is attractive in an educational setting because the resulting model is small enough to be served locally, which avoids both recurring API charges and the transmission of student work to an external provider.

 Fine-tuning is not, however, a general remedy. A distinction that proved central to this project is between properties a model can be taught by example and properties it cannot. The structure of an output is a formatting behaviour that a modest number of examples can teach. Determining what a particular piece of Python returns for a particular input is not a formatting behaviour; it is interpretation, and a small model performs it unreliably regardless of how many examples of correct interpretation it has seen. Where a deterministic component is available to supply such a property, using it is preferable to attempting to train it.

*This partially closes Person 3's Block G2* (Background has no citations). The remaining
uncited claims — adaptive formative assessment, and AI-augmented code execution tools — can
draw on Bloom (1968), Vygotsky (1978), Corbett and Anderson (1994) and Pelánek (2017), all
of which are in the merged reference list.

---

## Part C — Section text

### C.1 — 3.4 Adaptive Recommender Engine *(Person 3, verbatim)*


The adaptive recommender is the component that converts assessment into progression. After each submission it receives the sandbox outcome, the evaluator's scores, and the learner's session history, and returns a decision either to reinforce at the current level or to advance to a harder question, together with a specific next question and a confidence value. The design follows the mastery-learning principle that progression should be gated on demonstrated competence rather than on completion alone (Bloom, 1968), and targets the band immediately beyond independent performance (Vygotsky, 1978).

Nine features are supplied to the classifier (`recommender/features.py`). Four describe the  current attempt: the question's difficulty, its topic, the number of submissions made on it including the one being judged, and whether that submission passed. Four summarise the  session: the pass rate across all attempts, the mean efficiency and style scores across all graded attempts, and the most recent efficiency and style scores. Topic is one-hot encoded across the seventeen topics present in the dataset, giving twenty-five encoded columns in total. Difficulty is used as an ordinal integer without scaling, since decision trees split on thresholds rather than distances and are therefore invariant to monotone transformations of their inputs (Hastie et al., 2009). Because failed submissions are never sent to the evaluator, the score features carry forward from the last graded attempt, and a learner with no history receives mid-scale defaults of 0.5 for pass rate and 3 for each score, so that a new user is assumed neither competent nor struggling. Training and serving encode through the same function, which makes divergence between training-time and serving-time features structurally impossible rather than a matter of review discipline, a failure mode identified as one of the characteristic hidden costs of production machine-learning systems (Sculley et al., 2015).

Supervised learning requires labelled targets, and no external source supplies them for the question "what should this learner attempt next?". A pedagogical labelling policy was therefore defined explicitly (`recommender/labeling.py`) and used to generate the training targets. The policy advances a learner who passes within two attempts with an efficiency score of at least four, on the grounds that few attempts indicate the approach was held in advance rather than reached by trial and error, and a high efficiency score indicates a sound algorithm rather than merely a passing one. It also advances a learner who passes with a session pass rate of at least 0.75 and an efficiency score of at least three, which accommodates the consistent performer who happened to labour on one question. All other outcomes, including every failure, reinforce; this is the conservative default, since an additional question at the same level costs a learner time whereas premature advancement costs comprehension.

Because no real learner data existed during development, the classifier was trained on simulated trajectories (`recommender/simulate.py`). Five archetypes: struggler, average, advanced, fast improver and inconsistent, were parameterised with distinct pass probabilities per difficulty level, distinct score profiles, and distinct improvement rates, and each simulated learner completed between five and twenty questions drawn from the real question set. Score distributions were not invented but calibrated against fifteen recorded outputs of the deployed evaluator, which never produced an efficiency score of two or a style score of one and whose efficiency scores were bimodal rather than bell-shaped; scores were therefore drawn from discrete weights reflecting those observations. Every random operation is seeded, so the dataset regenerates identically. Training on generated data is an established response to data scarcity, subject to the caveat that results transfer only insofar as the generator resembles reality (Nikolenko, 2021).

The model is a decision-tree classifier (Breiman et al., 1984) implemented with scikit-learn (Pedregosa et al., 2011) and configured with a maximum depth of three, a minimum of twenty samples per leaf, and balanced class weights. Because successive rows from one simulated learner share an archetype, a running pass rate and a difficulty trajectory, an ordinary row-wise split would place correlated observations on both sides of the boundary and inflate every metric; whole learners were therefore held out using grouped splitting on the learner identifier, which is the standard remedy for structured dependence (Roberts et al., 2017; Kaufman et al., 2012). Depth was selected from a grouped cross-validated sweep rather than assumed. At serving time (`recommender/engine.py`) the decision is mapped to a target difficulty and then to a concrete question, subject to guardrails: a learner who fails is offered the same question again up to three times before being moved sideways, no question is served twice in a session, the search widens to the nearest difficulty if the target level is exhausted, and the engine falls back to a hand-written rule if no trained model is present. Every decision is appended to a prediction log for subsequent analysis.

### C.2 — 3.5 Fine-Tuned Question Generation *(new)*

 The Custom Practice feature required a model that returns a complete question record in the schema used by `data/questions/`, so that generated questions could be executed, graded and recommended by the components already described. General instruction-tuned models did not do this reliably, so a model was fine-tuned for the task.
 
 **Base model and method.** The base model was `Qwen2.5-Coder-3B-Instruct`, loaded in 4-bit  precision. A code-specialised base was chosen over a general-purpose model of similar size because the task requires writing valid Python as well as valid JSON. Adaptation used QLoRA (Dettmers et al., 2023) with rank 16 and scaling factor 16, applied to all seven linear projections of each transformer block, trained for two epochs with an effective batch size of eight, a learning rate of 2 × 10⁻⁴ under a linear schedule, and 8-bit AdamW. Loss was  computed on the assistant response only, so that model capacity was not spent learning to reproduce the instruction it is always given. Training was performed on a single T4 GPU and completed in approximately two and a half hours.
 
 **Training data.** The training data is the same keep-pile described in 3.1, the 2,599 problems that survived compatibility filtering, rather than the stratified sample of 50 used for the question bank. Each example pairs an instruction naming a topic and difficulty with a target containing the six fields the model must produce: title, description, starter code, entry point, reference solution and test cases. The remaining schema fields are bookkeeping and are filled in by the application. Critically, the split between training and evaluation data was made **by topic rather than at random**. A random split would allow the model to be evaluated on a topic it had memorised during training, which measures recall; holding out entire topics measures whether the model can produce a valid record for a topic it has never seen, which is what a student typing a free-text topic actually requires.


 **Prompt sharing.** The system prompt, the instruction format and the list of taught fields are defined once in `evaluator/generate.py` and imported by the training notebook. A model trained against one prompt and served under another is a common and difficult-to-diagnose failure, in which a correctly trained model appears broken. An automated test asserts that the system prompt stored in the Ollama Modelfile remains byte-identical to the one used in training.

**Deployment.** After training, the adapters were merged into the base weights and quantised to `q4_k_m`, producing a 1.84 GB file that runs locally under llama.cpp (Gerganov et al., n.d.) or Ollama. This keeps the generator consistent with the platform's bring-your-own-model architecture: student code and generated questions remain on the machine.

**Establishing test cases by execution.** The schema originally required the model to write each test case as an input together with its expected output. This asks the model to state,
from memory, what its own reference solution returns for a given input, an act of interpretation rather than formatting. Measured on held-out topics, the model never once produced a complete set of test cases that its own solution passed (see 4.4).

The final design therefore does not ask. After a generated record is parsed, the model's reference solution is executed in the sandbox against the model's test *inputs*, and the values actually returned become the expected outputs. Self-consistency then holds by construction for every test case whose execution succeeds. The same subprocess isolation, static security analysis and five-second timeout described in 3.2 apply, because model-written code is treated with no more trust than student-written code.

Four conditions reject a generated question at this stage: a solution that does not execute; a test case that raises an exception; a returned value that cannot survive serialisation unchanged, such as a tuple, which would otherwise compare unequal when reloaded; and a set of computed outputs that are all identical, which would yield a question that a one-line stub could pass. A question surviving all four is then verified once more through the ordinary sandbox path before it is served.

### C.3 — 4.3 Recommender Model Benchmarking *(Person 3, verbatim)*

Replaces both placeholders under 4.3.

> The simulator produced 2,460 decision points from 200 simulated learners, split 55.1%
> reinforce and 44.9% advance. The classes proved closer to balanced than anticipated because
> the serving policy is self-correcting: advancement raises difficulty, which lowers the pass
> rate, which returns the learner to reinforcement. Balanced class weighting was retained
> regardless, since the balance is a property of this particular simulator rather than a
> guarantee, and class imbalance is a well-documented source of misleadingly high accuracy
> (He & Garcia, 2009). Two checks confirmed the generator behaved as specified. The
> advancement rate was monotone in designed ability, rising from 14.8% for strugglers through
> 40.6% for inconsistent learners, 42.5% for average learners and 51.7% for fast improvers to
> 80.9% for advanced learners. Fast improvers climbed from 30.0% advancement in the first four
> questions of a session to 81.9% from the tenth question onward, confirming that the
> improvement mechanism operated as intended.
>
> Depth was selected by grouped five-fold cross-validation over the candidate range two to
> eight (Figure 4.x). Macro-averaged F1 was 0.909 at depth two and 0.998 at every depth from
> three to eight. Depth two is therefore clearly underfit and performance is flat thereafter;
> depth three was selected as the smallest depth on the plateau, with interpretability
> breaking the tie, since the ability to display and defend the complete decision procedure is
> a deliverable of this project rather than an incidental property (Rudin, 2019).
>
> The trained classifier was evaluated against a hand-written rule baseline on 631 decisions
> from 50 learners held out entirely from training. The baseline advances a learner who passed
> on the first attempt with an efficiency score of at least three; it was written to be
> reasonable rather than to be beaten, since a comparison against a deliberately weak
> alternative would carry no information.
>
> *[Table 4.x here — see C.4]*
>
> These figures require careful interpretation, and reporting them without qualification would
> overstate what was achieved. The labelling policy described in Section 3.4 is a function of
> four quantities, whether the attempt passed, how many attempts it required, the efficiency
> score, and the session pass rate, and all four are available to the classifier as features.
> The learning task is therefore close to recovering a known three-branch rule from its own
> inputs, which a tree of depth three can represent almost exactly, and which also explains
> why cross-validated performance is flat from depth three onward. The result establishes that
> feature assembly, encoding, training and serving faithfully reproduce the intended policy;
> it does not establish that the policy itself is pedagogically sound. The margin over the
> rule baseline should be read in the same way: it quantifies the divergence between two
> policies rather than demonstrating the superiority of either.
>
> Inspection of the learned tree (Figure 4.y) supports this reading. The model splits on the
> most recent efficiency score at thresholds of 2.0 and 3.5, on the session pass rate at 0.74,
> on whether the last attempt passed, and on the number of attempts at 2.5, that is, on
> precisely the quantities the labelling policy uses, with thresholds recovered where the
> written rule places them. Permutation importance computed on the held-out learners (Figure
> 4.z) concentrates entirely on those same features (Fisher et al., 2019). Notably, all
> seventeen topic indicators received zero importance and the tree never split on topic or on
> question difficulty. This is reported as a finding rather than omitted: with 50 questions
> distributed across 17 topics, 22 of which are Array problems and 10 of which contain a
> single question, topic carries no learnable signal at this dataset size. The feature was
> retained in the interface so that a larger question bank could exploit it without a schema
> change.

**Optional paragraph** — include only if the human-rating study is completed before
submission. Delete otherwise; do not populate it from the synthetic figures above, which
measure a different thing.

> To test whether the classifier's decisions correspond to human judgement, 15 decision points
> were sampled from live sessions and rated independently by all four team members, who saw
> the feature values but not the model's output. Majority vote served as the reference
> standard. The classifier agreed with the human majority on **[x] of 15** cases (**[x]%**)
> and the rule baseline on **[x] of 15** (**[x]%**); raters were unanimous on **[x]** cases,
> which bounds the agreement attainable by any system. Percentage agreement is reported rather
> than a chance-corrected coefficient such as Cohen's κ (Cohen, 1960), because at this sample
> size the latter would imply a precision the data do not support.

### C.4 — Figures and table for 4.3

All three figures exist at `docs/report/figures/` and `recommender/figures.py` is present;
regenerate with `python -m recommender.figures` only if the model is retrained.

| Placeholder | File | Caption |
|---|---|---|
| Figure 4.x | `depth_sweep.png` | Grouped cross-validated macro F1 by maximum tree depth. Performance plateaus from depth three. |
| Figure 4.y | `decision_tree.png` | The trained decision tree (depth three, balanced class weights). |
| Figure 4.z | `feature_importance.png` | Permutation importance on held-out learners. All topic indicators score zero. |

**Table 4.x**
*Classifier and rule baseline on 631 held-out decisions from 50 unseen learners*

| Metric | Decision tree | Rule baseline |
|---|---|---|
| Accuracy | 0.997 | 0.767 |
| Macro F1 | 0.997 | 0.765 |
| Recall (advance) | 1.000 | 0.785 |
| Recall (reinforce) | 0.994 | 0.753 |

*Note.* Split by learner using GroupShuffleSplit with a fixed seed; no learner appears in
both the training and evaluation sets.

### C.5 — 4.4 Question-Generator Evaluation *(new)*

> The generator was evaluated on twenty held-out topics using the application's own acceptance
> checks, so that a question counted as successful only if the deployed system would have
> served it. Three measurements were recorded: whether the reply parsed as valid JSON, whether
> it contained all six taught fields, and whether the model's test cases were ones its own
> reference solution passed.
>
> **Table 4.4.1** — *Schema compliance on held-out topics (n = 20)*
>
> | Metric | Base model | Fine-tuned |
> |---|---|---|
> | Valid JSON | 0/20 | 13/20 |
> | All six fields present | 0/20 | 13/20 |
> | Test cases self-consistent | 0/20 | 0/20 |
>
> The fine-tune achieved what fine-tuning can achieve. A base model that produced no usable
> record at all produced one in roughly two-thirds of attempts after training, and the two
> schema figures are identical in every condition, that is, every reply that parsed as JSON
> contained all six fields, correctly named, with the entry point matching the starter code.
> The schema was not partially learned; it was learned.
>
> Self-consistency did not move. Across every measurement of every version, the model never
> produced a complete set of test cases that its own solution passed. Inspection of failures
> showed the pattern directly: reference solutions were frequently correct, while the expected
> values disagreed with them on one or two cases, for example `got 5, expected 3` 
> indicating a model that writes working code and then misreports what that code returns. This
> is the result that motivated the execution-based design in 3.5.
>
> **Effect of the execution-based pipeline.** With expected values computed rather than
> predicted, 19 of 50 requests (38%) produced a question that passed every acceptance check and
> was served to the interface, against a raw self-consistency of zero. In a live session, a
> generated question was answered with a solution written independently of the model's own,
> using a different algorithm, and passed all eight of its test cases, evidence that the
> questions are genuinely solvable rather than merely internally consistent.
>
> **A second training run did not improve on the first.** Because expected values are now
> computed, a second model was trained with them removed from the target schema, on the
> expectation that shorter outputs would reduce truncation. Evaluated at n = 50 with both
> models served under identical settings, the first model scored 33/50 on schema compliance
> against the second model's 26/50, with pipeline yields of 19/50 and 18/50 respectively.
> Neither difference is statistically significant (1.44 and 0.21 standard errors), and the
> first model was also faster. The retraining was therefore not adopted.
>
> **A note on measurement.** An earlier comparison appeared to show the second model
> outperforming the first. That result was an artefact: the two models had been measured under
> different server context settings, one of which was returning capacity errors during the
> run. Re-measuring under identical settings removed the effect. Over the course of this work,
> three separate apparent model differences were traced to configuration differences in the
> harness rather than to the models. This is recorded because it bears on how the other
> results in this report should be read: a difference between two numbers is evidence about a
> model only when both were produced by the same harness under the same settings.

### C.6 — 5. Limitations, recommender *(Person 3, verbatim)*

Place first in Limitations.

> The recommender's reported performance rests on synthetic data, and this is its principal
> limitation. Every figure in Section 4.3 was measured against behaviour generated by this
> project, so realism depends on the archetype parameters and the evaluator calibration
> described in Section 3.4, neither of which was validated against real learners. Relatedly,
> the reported accuracy is close to tautological: all four inputs to the labelling policy are
> available to the classifier as features, so the result principally demonstrates that a
> shallow tree can represent a three-branch rule. It validates the implementation pipeline
> rather than the pedagogy, and the model can be no better than the policy that generated its
> targets. The thresholds in that policy are defensible by reference to mastery learning but
> were not derived empirically, and any bias they contain is inherited in full.
>
> The model-selection procedure was also not fully nested. The depth sweep used grouped
> cross-validation across the whole dataset, including the learners later used for evaluation,
> so the reported metrics are mildly optimistic with respect to the choice of depth (Cawley &
> Talbot, 2010). Given that performance was flat from depth three to depth eight, the
> practical effect is small, but the procedure does not constitute clean nested
> cross-validation.
>
> The most influential feature, the most recent efficiency score, originates from a language
> model whose calibration set misclassified two of fifteen brute-force solutions, 
> specifically those whose inefficiency was concealed within a single loop. Language models
> used as judges are known to exhibit systematic biases (Zheng et al., 2023), and this noise
> propagates directly into the routing decision. The calibration is moreover model-specific:
> the simulator was tuned to the outputs of one local model, and a check against a different
> model produced efficiency scores the original never emitted, so results are valid only for
> the model actually used and the model identifier must be reported alongside them.
>
> Finally, the topic features are inert at this dataset size and were never used by the model,
> so no claim about topic-aware routing is supported by this work; the recommender has no
> memory across sessions and no per-skill representation, so it cannot express which topics a
> learner has mastered, which is the concern addressed by knowledge-tracing approaches
> (Corbett & Anderson, 1994; Pelánek, 2017); and the confidence value should be read as an
> ordinal signal rather than a probability, since decision-tree class probabilities are known
> to be poorly calibrated (Niculescu-Mizil & Caruana, 2005).

### C.7 — 5. Limitations, generator *(new)*

Place after C.6.

> The question generator is limited by the capacity of a 3-billion-parameter model. Roughly a
> third of requests produce output that cannot be parsed, in most cases because the model
> enters a repetitive loop and emits the same fragment until it reaches the token limit. A
> decoding-level remedy was tested, a sampler penalising repeated sequences, and rejected:
> it improved parse rates but corrupted the generated Python, which contains legitimate
> repetition, reducing the proportion of parsed questions that were servable from 77% to 31%.
>
> The requested difficulty is not honoured. A request for a hard question typically returns a
> problem of easy or medium difficulty. This was investigated and is not a data problem: hard
> problems constituted a quarter of the training data and survived filtering at a higher rate
> than either other band. The difficulty label reaches the model as a single adjective
> competing with a topic that determines the entire problem domain, and the model appears to
> condition on the stronger signal.
>
> Computing expected values by execution guarantees that a question is solvable and internally
> consistent, but not that its tests match its written description. A model that writes a
> correct solution to a slightly different problem than the one it described produces a
> coherent and solvable exercise that does not test what it claims to. This failure remains
> detectable only by human review.
>
> The evaluation sample sizes are small. Twenty and fifty requests give standard errors of
> roughly eleven and seven percentage points respectively, which is sufficient to establish
> that the fine-tune improved schema compliance from zero, but not to separate models that
> differ by a few points. Local inference on CPU also takes between one and four minutes per
> generated question, which is acceptable for practice but would not support a class working
> simultaneously on modest hardware.

### C.8 — 6. Ethical Considerations *(new section)*

> **Privacy.** The platform's bring-your-own-model architecture allows every model-dependent
> component hints, grading and question generation  to run against a locally hosted model,
> in which case student code is never transmitted to a third party. This was a design
> objective rather than an incidental property: a cloud endpoint is an option the user selects,
> not a default the system depends on. Where a cloud endpoint is used, the submitted code and
> the generated feedback leave the institution's control, and users should be informed of this
> before selecting one.
>
> **Fairness in automated grading.** Automated scoring of student work carries a risk of
> penalising surface characteristics rather than substance. The project's human rating guide
> explicitly instructs raters that style scores must reflect code structure and clarity, and
> must not be influenced by the language of comments, phrasing, or the linguistic origin of
> variable names. This concern applies with greater force to any component that assesses
> free-form English prose, where a student who understands the material but writes in a second
> language could be scored lower than a less capable but more fluent peer. Any future feature
> that judges written explanations should be evaluated against this risk before it is allowed
> to influence a student's progression.
>
> **Automated progression on an imperfect signal.** The recommender's most influential feature
> is an efficiency score produced by a language model, and that model has a measured blind
> spot: on the fifteen-solution calibration set it misjudged two brute-force solutions whose
> inefficiency was concealed inside a single loop. Language models used as judges are known to
> carry systematic biases (Zheng et al., 2023). A student affected by that blind spot is not
> merely given an inaccurate score; they are routed onto a different learning path as a
> consequence of it. Two design choices limit the harm  reinforcement is the conservative
> default, so noise more often costs a student time than advances them beyond their
> competence, and the recommender's decision is displayed rather than applied silently but
> the exposure is real and is treated more fully in Section 5.
>
> **Assessment integrity.** Because the grading prompt receives student code as input, a
> student could embed text in comments intended to instruct the model, for example, a comment
> asserting that the code has already been graded highly. The grading prompt therefore
> contains an explicit instruction to treat all text inside submitted code as material to be
> evaluated rather than as instructions to follow. This is an integrity measure as much as a
> security one: without it, the assessment would advantage students who know how to manipulate
> a language model.
>
> **Transparency.** Model-generated questions are recorded with a flag marking them as
> generated and are written to a separate directory from the curated question bank, so they
> cannot be mistaken for validated material or enter the recommender's evaluation pool. The
> recommender's decision is displayed in the interface rather than applied silently, so a
> student can see why a particular question was selected. Feedback produced by a language
> model is presented alongside deterministic test results, never in place of them.
>
> **Reliability and its disclosure.** The evaluation in 4.2, 4.3 and 4.4 documents specific,
> reproducible weaknesses: a grading model that misjudges complexity when an expensive
> operation is nested inside a single loop, a recommender whose accuracy is measured against
> its own labelling policy on simulated learners, and a generator that produces a servable
> question in roughly a third of attempts. Reporting these plainly is itself an ethical
> requirement. A tool that presents AI-generated judgements to students without characterising
> their error rate invites those judgements to be trusted more than the evidence supports.

### C.9 — 7. Discussion, recommender *(Person 3, verbatim — note the section moved from 6 to 7)*

> The recommender demonstrates that a simple, fully interpretable classifier is sufficient to
> drive adaptive progression in a system of this scale, and that the engineering discipline
> surrounding such a model matters at least as much as the model itself. Sharing a single
> encoding function between training and serving, holding out whole learners rather than
> individual observations, and selecting depth from a cross-validated sweep rather than by
> assumption were each consequential decisions; the fact that the learned tree recovers the
> intended policy's thresholds is the clearest available evidence that the pipeline contains
> no feature or labelling defect.
>
> The more instructive finding is a negative one. Because the labelling policy's inputs are all
> present as features, near-perfect accuracy on held-out simulated learners was close to
> guaranteed, and it would have been straightforward to present that figure as evidence that
> machine learning outperforms rule-based gating. It is not such evidence. This illustrates a
> general risk in applying supervised learning to a problem whose labels are themselves
> generated by a rule: the model can only recover the rule, and the apparent margin over an
> alternative rule measures disagreement between two policies rather than the merit of either.
> The claim the project can legitimately support is narrower than the headline number suggests,
>  that a learned gate reproduces an explicit pedagogical policy faithfully and degrades
> gracefully on incomplete inputs and establishing whether that policy is pedagogically sound
> requires agreement with human judgement, not further work on the classifier.
>
> The choice of a depth-three decision tree over a more expressive model was therefore
> deliberate rather than a concession. In a setting where decisions affect learners, a model
> whose complete logic can be printed, read and contested is preferable to a more opaque one of
> comparable accuracy (Rudin, 2019; Doshi-Velez & Kim, 2017), and where cross-validated
> performance is flat across depths there is no accuracy to trade away. The practical value the
> classifier adds over executing the rule directly is correspondingly modest but real: it
> consumes the incomplete and noisy feature vector the application actually holds rather than
> requiring clean inputs, it produces a graded confidence signal that a boolean cannot, and it
> can be retrained on real session data as that data accumulates, whereas a hand-written rule
> improves only when someone rewrites it.

### C.10 — 8. Conclusion *(new section)*

> This project set out to determine whether deterministic testing, language models and adaptive
> selection could be combined into a programming assessment tool that is personalised, scalable
> and deployable without recurring cost. The resulting system executes submissions in an
> isolated sandbox, produces model-assisted feedback, recommends subsequent questions from
> measured performance, and generates new questions on demand from a locally hosted fine-tuned
> model.
>
> Two findings recur across the components and are the most transferable outcomes of the work.
> The first concerns the division of labour between learned and deterministic parts of a
> system. Fine-tuning reliably taught a small model the structure of the platform's question
> schema, taking schema compliance from zero to roughly two-thirds of attempts on unseen
> topics; the same training did not, and could not, teach the model to determine what its own
> code returns, a property that remained at zero across every version and prompt tested.
> Supplying that property from the execution environment instead of the model converted a
> component that produced no usable questions into one that produces a verified, solvable
> question in roughly a third of requests. A property a deterministic component can establish
> should not be trained, and identifying which properties those are is the more consequential
> design decision.
>
> The second concerns the interpretation of favourable numbers. The recommender's 99.7%
> accuracy and the generator's apparent improvement after retraining were both, on inspection,
> weaker evidence than they first appeared  the former because the classifier had access to
> every input of the policy that generated its labels, the latter because two models had been
> compared under different harness configurations. Both are reported here with those
> qualifications attached. In a system whose outputs shape what a student is asked to do next,
> the discipline of establishing what a measurement does not show is not a caveat appended to
> the results; it is part of the result.

### C.11 — Appendix A: AI Use Declaration *(new)*

> **This is a team-level statement and currently reflects one member's tool use. Each member
> should add their own before submission.**
>
> Generative AI tools were used during the development of this project, as follows.
>
> **Within the system.** The platform is itself an application of language models. Feedback,
> grading and question generation are produced by models accessed through a configurable
> endpoint. The question generator is a model fine-tuned by the team for this project; training
> configuration, data preparation and evaluation are described in 3.5 and 4.4, and the notebook
> that produces it is included in the repository.
>
> **In development.** An AI coding assistant was used during implementation and debugging of
> the generation pipeline, the evaluation harnesses and parts of the documentation. Its use
> included diagnosing failures, drafting code, and drafting sections of this report for review.
> All measurements reported were produced by executing the described harnesses; no result in
> this report was generated or estimated by an assistant. Every figure in 4.4 corresponds to a
> scorecard file committed to the repository.
>
> **Author responsibility.** The design decisions, the interpretation of results and the final
> text are the authors'. Where an assistant's initial conclusion was contradicted by subsequent
> measurement — most notably the comparison of the two training runs discussed in 4.4 — the
> corrected result is what appears here.

---

## Part D — Merged reference list

Alphabetical, deduplicated, covering every in-text citation across both contributions.
Verify page numbers and DOIs against the publisher record before submission; the three
arXiv identifiers in particular should be confirmed.

Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment, 1*(2), 1–12.

Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984). *Classification and
regression trees*. Wadsworth.

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent
selection bias in performance evaluation. *Journal of Machine Learning Research, 11*,
2079–2107.

Cohen, J. (1960). A coefficient of agreement for nominal scales. *Educational and
Psychological Measurement, 20*(1), 37–46. https://doi.org/10.1177/001316446002000104

Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of
procedural knowledge. *User Modeling and User-Adapted Interaction, 4*(4), 253–278.
https://doi.org/10.1007/BF01099821

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). *QLoRA: Efficient
finetuning of quantized LLMs* (arXiv:2305.14314). arXiv. https://arxiv.org/abs/2305.14314

Doshi-Velez, F., & Kim, B. (2017). *Towards a rigorous science of interpretable machine
learning* (arXiv:1702.08608). arXiv. https://arxiv.org/abs/1702.08608

Fisher, A., Rudin, C., & Dominici, F. (2019). All models are wrong, but many are useful:
Learning a variable's importance by studying an entire class of prediction models
simultaneously. *Journal of Machine Learning Research, 20*(177), 1–81.

Gerganov, G., et al. (n.d.). *llama.cpp* [Computer software]. GitHub.
https://github.com/ggml-org/llama.cpp

Hastie, T., Tibshirani, R., & Friedman, J. (2009). *The elements of statistical learning:
Data mining, inference, and prediction* (2nd ed.). Springer.
https://doi.org/10.1007/978-0-387-84858-7

He, H., & Garcia, E. A. (2009). Learning from imbalanced data. *IEEE Transactions on
Knowledge and Data Engineering, 21*(9), 1263–1284. https://doi.org/10.1109/TKDE.2008.239

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W.
(2021). *LoRA: Low-rank adaptation of large language models* (arXiv:2106.09685). arXiv.
https://arxiv.org/abs/2106.09685

Hui, B., et al. (2024). *Qwen2.5-Coder technical report* (arXiv:2409.12186). arXiv.
https://arxiv.org/abs/2409.12186

Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining:
Formulation, detection, and avoidance. *ACM Transactions on Knowledge Discovery from Data,
6*(4), Article 15. https://doi.org/10.1145/2382577.2382579

newfacade. (n.d.). *LeetCodeDataset* [Data set]. Hugging Face.
https://huggingface.co/datasets/newfacade/LeetCodeDataset

Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised
learning. In *Proceedings of the 22nd International Conference on Machine Learning*
(pp. 625–632). https://doi.org/10.1145/1102351.1102430

Nikolenko, S. I. (2021). *Synthetic data for deep learning*. Springer.
https://doi.org/10.1007/978-3-030-75178-4

Pedregosa, F., Varoquaux, G., Gramfort, A., Michel, V., Thirion, B., Grisel, O., Blondel, M.,
Prettenhofer, P., Weiss, R., Dubourg, V., Vanderplas, J., Passos, A., Cournapeau, D.,
Brucher, M., Perrot, M., & Duchesnay, É. (2011). Scikit-learn: Machine learning in Python.
*Journal of Machine Learning Research, 12*, 2825–2830.

Pelánek, R. (2017). Bayesian knowledge tracing, logistic models, and beyond: An overview of
learner modeling techniques. *User Modeling and User-Adapted Interaction, 27*(3), 313–350.
https://doi.org/10.1007/s11257-017-9193-2

Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G.,
Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle,
B. A., Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with
temporal, spatial, hierarchical, or phylogenetic structure. *Ecography, 40*(8), 913–929.
https://doi.org/10.1111/ecog.02881

Rudin, C. (2019). Stop explaining black box machine learning models for high stakes decisions
and use interpretable models instead. *Nature Machine Intelligence, 1*(5), 206–215.
https://doi.org/10.1038/s42256-019-0048-x

Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T., Ebner, D., Chaudhary, V.,
Young, M., Crespo, J.-F., & Dennison, D. (2015). Hidden technical debt in machine learning
systems. In *Advances in Neural Information Processing Systems* (Vol. 28, pp. 2503–2511).

Vygotsky, L. S. (1978). *Mind in society: The development of higher psychological processes*.
Harvard University Press.

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D.,
Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with
MT-Bench and Chatbot Arena. In *Advances in Neural Information Processing Systems* (Vol. 36).

---

## Part E — Consolidated corrections to text already written

Flagged rather than silently changed, since these are other members' sections.

**E.1 — The BYOM description is out of date (§3.3, and §1.3 objective 3).**
The text says the system supports "a local Ollama/Gemma model and the OpenAI cloud API". The
implementation is not restricted to those two: the provider name determines nothing, and any
OpenAI-compatible endpoint works — Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq,
OpenRouter, Together, or a custom gateway — configured by URL, key and model name in the
interface.

Suggested replacement for the §3.3 sentence:

> It uses a bring-your-own-model architecture in which the endpoint URL, credentials and model
> name are supplied at runtime, so any OpenAI-compatible service — whether a locally hosted
> model or a hosted API — can be substituted without code changes, allowing the trade-off among
> cost, latency and privacy to be adjusted per deployment.

This matters beyond accuracy: provider-independence is the strongest support for the
accessibility argument in §1.1 and §1.4, and the current text understates it. The §1.3
objective is rewritten in **B.3**. The Abstract does **not** need this change — its wording is
already provider-neutral.

**E.2 — Section 2 (Background) has no citations.** Partially closed by **B.4**, which adds two
cited paragraphs. The remaining uncited claims — "research on adaptive formative assessment
suggests…" and "recent educational tools have combined code execution with AI-generated
explanations" — can draw on Bloom (1968), Vygotsky (1978), Corbett and Anderson (1994) and
Pelánek (2017), all now in the reference list.

**E.3 — Test-case counts.** §1.1 states "100+" test cases per question. Verified against the
50 selected questions: the range is **37 to 234**, mean **99.6**, median **99**, with **26 of
50 below 100**. "Typically around 100" is accurate; "100+" is not.

**E.4 — The abstract promises evaluation of "cost" and "fairness".** Fairness is now delivered
by section 6. **Cost is still not reported in any section.** Either add a result — inference
latency and the absence of per-call charges under local serving are both measurable — or
remove the word from the abstract.

**E.5 — Title page date.** 12 August 2026 predates the generator experiments reported in 4.4,
which ran 13–16 August. Update to the submission date.

**E.6 — §4.1, final sentence.** "…to have executable, and reproducible" → "to be executable
and reproducible".

**E.7 — §4.2 internal inconsistency.** The section reports 13/15 as the headline and later
says the prompt iterations left accuracy at "12-13 out of 15". Make the two statements
consistent, or state explicitly that the figure varied by run — which is itself a finding
worth keeping, given the run-to-run drift documented in `docs/gemma_scoring_notes.md`.
