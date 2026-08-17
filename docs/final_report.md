# 4ALL: An Adaptive AI Coding Assessment Platform

**Chuong Tiutiu Nyang Mayian · Fannareme Aboubacar Abdou · Frank Kwizera Mugwaneza ·
Tapiwanashe Mandiveyi**

Department of Computer Science and Information Systems, Ashesi University
CS254: Introduction to Artificial Intelligence
Dr. Daniel Addo
[submission date]

---

## Abstract

Programming assessment systems commonly give identical questions and feedback to learners of differing ability, while manual code review does not scale. This project presents 4ALL, an adaptive assessment platform combining deterministic testing, AI-assisted feedback, question recommendation and question generation. Submissions are screened by static analysis and executed in a sandboxed subprocess against a validated set of 50 Python problems. A bring-your-own-model evaluator, configurable against any OpenAI-compatible endpoint, produces conceptual hints and complexity judgements, matching 13 of 15 hand-labelled efficiency scores. A decision-tree recommender selects the next question. A fine-tuned 3-billion-parameter model generates new questions in the platform's schema, with each test case's expected output computed by executing the model's own solution rather than predicted by it, raising usable generated questions from none to roughly a third of requests. Evaluation identifies specific limits in complexity judgement, recommender validation and generation reliability.

---

## 1. Introduction

Conventional programming assessment systems present fixed questions and standardised feedback to learners of widely differing ability: beginners meet tasks that frustrate them, stronger students meet tasks that do not extend them. Manual review produces better feedback but does not scale, applies standards inconsistently, and leaves students waiting (Bito, 2025).

Language models offer automated explanation and code-quality analysis, but bring their own difficulties. Cloud services carry recurring cost, rate limits, and the privacy exposure of transmitting student work to an external provider; local models avoid these but demand hardware and generally perform less well (Ultra Lab, 2026). Those constraints bind hardest where reliable connectivity and paid services cannot be assumed.

This project developed **4ALL** to address these together. Its objectives were to build and validate a dataset of Python questions with executable test cases; execute submissions securely under static analysis and an isolated, time-limited subprocess; design a bring-your-own-model architecture in which any OpenAI-compatible endpoint is configurable at runtime; generate conceptual hints and complexity and style scores; recommend a subsequent question from measured performance; fine-tune a small, locally deployable model to generate new questions in the platform's schema, establishing their test cases by execution rather than by prediction; and evaluate each component, identifying the ethical issues and limitations arising.

## 2. Background
 Adaptive formative assessment adjusts difficulty to measured performance, an approach with demonstrated relevance to introductory programming (Thangaraj, 2025), resting on the mastery-learning principle that progression should follow demonstrated competence rather than completion (Bloom, 1968) and target the band just beyond independent performance (Vygotsky, 1978). Language models can supply the explanations that test results lack, but are unreliable enough to supplement deterministic testing rather than replace it; models used as judges exhibit systematic biases (Zheng et al., 2023).
 
 Generating practice material is a different problem from assessing it. An assessment platform needs not readable prose but a machine-readable record its sandbox, validator and recommender can all consume. Parameter-efficient fine-tuning, Low-Rank Adaptation (Hu et al., 2021) and its quantised variant QLoRA (Dettmers et al., 2023), makes adapting a model to a fixed output format feasible on modest hardware, yielding a model small enough to serve locally.
 
 Fine-tuning is not a general remedy, and the distinction that proved central to this project is between properties a model can be taught by example and properties it cannot. The *structure* of an output is a formatting behaviour examples teach well. Determining what a piece of Python returns for a given input is not formatting but interpretation, and a small model performs it unreliably however many examples it sees. Where a deterministic component can supply such a property, using it is preferable to training it.

## 3. Methodology

**Data.** The question bank derives from LeetCodeDataset (Xia et al., 2025; newfacade, n.d.), originally 2,869 problems. Filtering removed problems requiring multiple solution methods, unsupported tree or linked-list structures, third-party libraries, or unusable test cases, leaving 2,599. From these, a seeded stratified sample of 50 was drawn: 20 easy, 20 medium,and  10 hard, spanning multiple topics. Test cases were normalised to a uniform input/expected structure, and input expressions parsed via AST rather than `eval()`.

**Assessment and feedback.** Correctness is determined deterministically, by static security analysis followed by sandboxed execution against the normalised test cases. A bring-your-own-model evaluator then produces conceptual hints for failures and, for passes, a few-shot prompt estimating time complexity and scoring efficiency and style against a rubric.

**Recommendation.** A decision-tree classifier (Breiman et al., 1984; Pedregosa et al., 2011) maps nine features — the current question's difficulty and topic, attempts, pass/fail, and session-level pass rate and score summaries — to a decision to reinforce or advance. No external source labels "what should this learner attempt next", so an explicit pedagogical policy generated the targets: advance on a pass within two attempts at efficiency ≥ 4, or on a pass with session pass rate ≥ 0.75 and efficiency ≥ 3; otherwise reinforce. Reinforcement is the conservative default, since an extra question costs time whereas premature advancement costs comprehension. With no real learner data available, training used 2,460 decision points from 200 simulated learners across five archetypes, calibrated against recorded evaluator outputs — a standard response to data scarcity, valid only insofar as the generator resembles reality (Nikolenko, 2021).

**Generation.** `Qwen2.5-Coder-3B-Instruct` (Hui et al., 2024) was adapted with QLoRA (rank 16, all seven linear projections, two epochs) on the 2,599-problem keep-pile, learning to emit six fields: title, description, starter code, entry point, reference solution and test cases. Training and evaluation were split **by topic rather than at random**, so the metric measures generalisation to unseen topics rather than recall. The merged model was quantised and served locally under llama.cpp (Gerganov et al., n.d.), keeping student code on the machine.

## 4. Implementation

Four design decisions shaped the system more than any other.

**Untrusted code is isolated, and model-written code counts as untrusted.** An AST check rejects dangerous imports, `eval`, `exec`, `open` and dunder-attribute access before anything executes; execution then happens in a fresh subprocess under a timeout, so a non-terminating or hostile submission cannot affect the application. Generated questions take the identical path: a model's reference solution receives no more trust than a student's.

**Training and serving share one definition.** The recommender's features come from the same encoding code in both, making training/serving skew structurally impossible rather than a matter of review discipline, a characteristic hidden cost of production machine-learning systems (Sculley et al., 2015). The generator follows the same rule: its system prompt is defined once and imported by the training notebook, with a test asserting the deployed copy stays byte-identical. A model trained on one prompt and served under another fails in a way that looks like a broken model rather than a broken configuration.

**Evaluation holds out whole learners, not rows.** Successive decisions from one simulated learner share an archetype and a difficulty trajectory, so a row-wise split would place correlated observations either side of the boundary and inflate every metric. Grouped splitting on learner identity is the standard remedy for such structured dependence (Roberts et al., 2017).

**Expected outputs are computed, not predicted.** The generator's schema originally required the model to supply each test case's expected value, to state from memory what its own code returns. On held-out topics it never once produced a complete set of test cases its own solution passed. The final design does not ask: the reference solution is executed against the model's test *inputs*, and the values returned become the expected outputs, so self-consistency holds by construction. Four conditions then reject a question: a solution that does not run; a case that raises; a value that cannot survive serialisation unchanged, such as a tuple, which would compare unequal when reloaded; and outputs that are all identical, which would yield a question a one-line stub could pass.

## 5. Results & Evaluation

### 5.1 Dataset

All 50 questions passed structural validation with zero errors, and all 50 reference solutions executed successfully against their normalised test cases. Test-case counts range from 37 to 234 (mean 99.6).

### 5.2 Evaluator

Against a hand-labelled golden set of 15 solutions spanning five problems at three quality levels, the evaluator matched **13 of 15** efficiency scores (86.7%), and the defensive parser recovered a structured result for all 15. The two misses shared a cause: both were brute-force solutions whose expensive operation; string concatenation, repeated `.replace()` sat *inside* a single loop, which the model read as linear. Prompt revisions targeting this blind spot changed which cases failed without improving the total, and one regressed; accuracy varied between 12 and 13 of 15 across runs, so the figure is approximate rather than exact.

### 5.3 Recommender

Depth was selected by grouped five-fold cross-validation (Figure 1): macro-F1 was 0.909 at depth two and 0.998 from depth three onward, so depth three was chosen as the smallest on the plateau, interpretability breaking the tie (Rudin, 2019).

**Table 1.** *Classifier and rule baseline, 631 decisions from 50 unseen learners*

| Metric | Decision tree | Rule baseline |
|---|---|---|
| Accuracy | 0.997 | 0.767 |
| Macro F1 | 0.997 | 0.765 |
| Recall (advance) | 1.000 | 0.785 |
| Recall (reinforce) | 0.994 | 0.753 |

**These figures require qualification, and reporting them without it would overstate the result.** The labelling policy is a function of four quantities: pass, attempts, efficiency score, session pass rate, and all four are available to the classifier as features. The task is therefore close to recovering a known three-branch rule from its own inputs, which a depth-three tree represents almost exactly, and which also explains why performance is flat beyond depth three. The result establishes that feature assembly, encoding, training and serving reproduce the intended policy faithfully; it does **not** establish that the policy is pedagogically sound. The margin over the baseline measures divergence between two policies, not the merit of either.

Inspection supports this reading. The tree splits on recent efficiency, session pass rate, whether the last attempt passed and the number of attempts — the labelling policy's own quantities, at its own thresholds (Figure 2) — and permutation importance concentrates on exactly those (Fisher et al., 2019). All seventeen topic indicators score zero (Figure 3): with 50 questions across 17 topics, topic carries no learnable signal at this scale.

### 5.4 Question generator

The generator was evaluated on held-out topics using the application's own acceptance checks, so a question counted as successful only if the deployed system would have served it.

**Table 2.** *Schema compliance on held-out topics (n = 20)*

| Metric | Base model | Fine-tuned |
|---|---|---|
| Valid JSON | 0/20 | 13/20 |
| All six fields present | 0/20 | 13/20 |
| Test cases self-consistent | 0/20 | 0/20 |

The fine-tune achieved what fine-tuning can achieve. A base model producing no usable record at all produced one in roughly two-thirds of attempts, and the two schema figures are identical in every condition: every reply that parsed contained all six fields, correctly named, with the entry point matching the starter code. The schema was not partially learned.

Self-consistency did not move. Across every version the model never produced a complete set of test cases its own solution passed; reference solutions were frequently correct while the stated expected values disagreed with them on one or two cases, indicating a model that writes working code and then misreports what it returns. With expected values computed instead, **19 of 50 requests (38%)** produced a question passing every acceptance check, and one was then solved by an independently written solution using a different algorithm — evidence that these questions are genuinely solvable, not merely self-consistent.

A second model, trained with expected values removed from the target schema so that shorter outputs might reduce truncation, did not improve on the first: at n = 50 under identical settings it scored 26/50 against 33/50, with pipeline yields of 18/50 and 19/50. Neither difference is significant (1.44σ and 0.21σ) and the first model was faster, so the retraining was not adopted.

**A note on measurement.** An earlier comparison appeared to favour the second model. It was an artefact: the two had been measured under different server context settings, one of which was returning capacity errors mid-run. Over this work, three separate apparent model differences proved to be harness configuration differences. This bears on how every figure above should be read, a difference between two numbers is evidence about a model only when both came from the same harness under the same settings.

## 6. Ethical Considerations

**Privacy.** Every model-dependent component can run against a locally hosted model, in which case student code never leaves the machine; a cloud endpoint is a choice the user makes, not a dependency the system carries. Where one is used, students should be told their code is processed externally, and prompts should carry no names, identifiers or credentials.

**Automated progression on an imperfect signal.** The recommender's most influential feature is an efficiency score produced by a language model, and that model has a measured blind spot: it misjudged two of fifteen calibration solutions whose inefficiency was concealed inside a single loop (§5.2). Language-model judges carry systematic biases (Zheng et al., 2023). A student affected is not merely scored inaccurately, they are routed onto a different learning path as a consequence. Two choices limit the harm: reinforcement is the conservative default, so noise more often costs a student time than advances them beyond their competence, and the recommender's decision is displayed rather than applied silently. The exposure nonetheless remains, and is the strongest argument in this report against using the system for anything summative.

**Fairness.** Style scores must reflect code structure and clarity, never the language of comments, phrasing, or the linguistic origin of variable names; the project's rating guide instructs human raters accordingly, and the same standard binds the model. The risk sharpens for any future component judging written English, where a student who understands the material but writes in a second language could score below a more fluent but weaker peer, a live concern in a multilingual cohort.

**Integrity.** Because student code enters the grading prompt, a comment could attempt to instruct the model, for instance by asserting the work has already been graded highly. The prompt therefore treats all text inside a submission as material to be evaluated, never as instructions to follow; without this the assessment would advantage students who know how to manipulate a language model.

**Transparency.** Deterministic results are presented separately from model interpretations: "three of five test cases failed" is evidence, "your algorithm is probably quadratic" is a judgement that may be wrong. Generated questions are flagged and stored apart from the curated bank, and recommender decisions are shown with the performance that produced them. The error rates in §5.2–5.4 are reported plainly, because presenting AI judgements without characterising their reliability invites more trust than the evidence supports.

## 7. Limitations & Future Work

The recommender rests on synthetic data, and its accuracy is close to tautological: every input to the labelling policy is a feature, so the result shows a shallow tree can represent a three-branch rule. It validates the implementation, not the pedagogy, and the model can be no better than the policy generating its targets, a policy whose thresholds are defensible by reference to mastery learning but were not derived empirically. Model selection was not fully nested either: the depth sweep used the whole dataset, so the metrics are mildly optimistic with respect to the choice of depth (Cawley & Talbot, 2010). The confidence value is an ordinal signal, not a probability (Niculescu-Mizil & Caruana, 2005), and the topic features were never used, so no claim about topic-aware routing is supported here.

The generator is limited by a 3-billion-parameter model. Roughly a third of requests produce unparseable output, usually because the model enters a repetitive loop until it reaches the token limit; a sampler penalising repeated sequences was tested and rejected, because it corrupted the generated Python, which contains legitimate repetition. Requested difficulty is not honoured, and this is not a data problem: hard problems were a quarter of the training data and survived filtering at a higher rate than either other band. Computing expected values guarantees a question is solvable and self-consistent but not that its tests match its description, which remains detectable only by human review. Sample sizes are small — 20 and 50 requests give standard errors near eleven and seven percentage points — and local CPU inference takes one to four minutes per question.

Future work follows directly. The most valuable step by some distance is replacing simulated learners with real, ethically collected interaction data, which would make the recommender's accuracy a claim about pedagogy rather than implementation and would test the archetype assumptions every figure in §5.3 rests on. Per-skill modelling along knowledge-tracing lines (Corbett & Anderson, 1994; Pelánek, 2017) and container-level sandbox isolation are the natural extensions once that data exists.

## 8. Conclusion

4ALL integrates dataset normalisation, sandboxed execution, AI-assisted feedback, adaptive recommendation and question generation. All 50 questions and reference solutions passed validation; the evaluator matched 13 of 15 efficiency scores; the recommender reproduced its labelling policy on held-out simulated learners; and the fine-tuned generator produced a verified, solvable question in roughly a third of requests.

Two findings generalise beyond this system. First, fine-tuning taught a small model the structure of the question schema but could not teach it to determine what its own code returns, a property supplied instead by the execution environment, which converted a component producing nothing usable into a working one. **A property a deterministic component can establish should not be trained, and identifying which properties those are is the more consequential design decision.** Second, both the recommender's 99.7% accuracy and the generator's apparent improvement after retraining proved weaker on inspection than they first appeared. In a system whose outputs shape what a student is asked to do next, establishing what a measurement does not show is part of the result rather than a caveat appended to it.

---

## References

Bito. (2025). *Manual vs. automated code review: A developer's guide.*
https://bito.ai/blog/manual-vs-automated-code-review/

Bloom, B. S. (1968). Learning for mastery. *Evaluation Comment, 1*(2), 1–12.

Breiman, L., Friedman, J. H., Olshen, R. A., & Stone, C. J. (1984). *Classification and
regression trees.* Wadsworth.

Cawley, G. C., & Talbot, N. L. C. (2010). On over-fitting in model selection and subsequent
selection bias in performance evaluation. *Journal of Machine Learning Research, 11*,
2079–2107.

Corbett, A. T., & Anderson, J. R. (1994). Knowledge tracing: Modeling the acquisition of
procedural knowledge. *User Modeling and User-Adapted Interaction, 4*(4), 253–278.
https://doi.org/10.1007/BF01099821

Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). *QLoRA: Efficient
finetuning of quantized LLMs* (arXiv:2305.14314). arXiv. https://arxiv.org/abs/2305.14314

Fisher, A., Rudin, C., & Dominici, F. (2019). All models are wrong, but many are useful:
Learning a variable's importance by studying an entire class of prediction models
simultaneously. *Journal of Machine Learning Research, 20*(177), 1–81.

Gerganov, G., et al. (n.d.). *llama.cpp* [Computer software]. GitHub.
https://github.com/ggml-org/llama.cpp

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W. (2021).
*LoRA: Low-rank adaptation of large language models* (arXiv:2106.09685). arXiv.
https://arxiv.org/abs/2106.09685

Hui, B., et al. (2024). *Qwen2.5-Coder technical report* (arXiv:2409.12186). arXiv.
https://arxiv.org/abs/2409.12186

newfacade. (n.d.). *LeetCodeDataset* [Data set]. Hugging Face.
https://huggingface.co/datasets/newfacade/LeetCodeDataset

Niculescu-Mizil, A., & Caruana, R. (2005). Predicting good probabilities with supervised
learning. In *Proceedings of the 22nd International Conference on Machine Learning*
(pp. 625–632). https://doi.org/10.1145/1102351.1102430

Nikolenko, S. I. (2021). *Synthetic data for deep learning.* Springer.
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

Thangaraj, J. (2025). Potential approaches for adaptive formative assessment to motivate
novices in introductory programming. In *Proceedings of the 2025 Conference on UK and Ireland
Computing Education Research*, Article 32. https://doi.org/10.1145/3754508.3754523

Ultra Lab. (2026). *Local LLM on NVIDIA GPU vs. cloud API: A real cost analysis.*
https://ultralab.tw/en/blog/local-llm-gpu-vs-cloud-api

Vygotsky, L. S. (1978). *Mind in society: The development of higher psychological processes.*
Harvard University Press.

Xia, Y., Shen, W., Wang, Y., Liu, J. K., Sun, H., Wu, S., Hu, J., & Xu, X. (2025).
*LeetCodeDataset: A temporal dataset for robust evaluation and efficient training of code
LLMs.* arXiv. https://doi.org/10.48550/arXiv.2504.14655

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., Lin, Z., Li, Z., Li, D.,
Xing, E. P., Zhang, H., Gonzalez, J. E., & Stoica, I. (2023). Judging LLM-as-a-judge with
MT-Bench and Chatbot Arena. In *Advances in Neural Information Processing Systems* (Vol. 36).

---

## Appendix A — Figures

**Figure 1.** Grouped cross-validated macro F1 by maximum tree depth. Performance plateaus
from depth three. *(`depth_sweep.png`)*

**Figure 2.** The trained decision tree, depth three, balanced class weights.
*(`decision_tree.png`)*

**Figure 3.** Permutation importance on held-out learners. All topic indicators score zero.
*(`feature_importance.png`)*

*Place these inline in §5.3 if space allows — they are the evidence for the paragraphs that
cite them.*

---

## Appendix B — AI Use Declaration

> **Each member should add a sentence covering their own tool use before submission.**

Generative AI is both a subject and a tool of this project.

**Within the system.** Hints, grading and question generation are produced by language models
accessed through a configurable endpoint. The question generator is a model fine-tuned by the
team for this project; its training configuration, data preparation and evaluation are
described in §3 and §5.4, and the notebook producing it is included in the repository.

**In development.** An AI coding assistant was used during implementation and debugging of the
generation pipeline and the evaluation harnesses, and to draft sections of this report for
review. All reported measurements were produced by executing the described harnesses; no
figure in this report was generated or estimated by an assistant. Each result in §5.4
corresponds to a scorecard file committed to the repository.

**Author responsibility.** The design decisions, the interpretation of results and the final
text are the authors'. Where an assistant's initial conclusion was later contradicted by
measurement — most notably the comparison of the two training runs in §5.4 — the corrected
result is what appears here.
