# Report review — harmony check and cut plan

## Part 1 — Harmony defects

Ordered by how badly they hurt. The first four are visible contradictions *within the
document*, which cost more than length ever will.

### 1.1 The Abstract contradicts objective 3 and §3.3 contradicts both

The Abstract says the evaluator supports **"local Ollama/Gemma and cloud-based models"**.
§3.3 says **"a local Ollama/Gemma model and the OpenAI cloud API"**. Objective 3 in §1.3
now says **"any OpenAI-compatible endpoint, locally hosted or remote"**.

Those are three descriptions of one architecture, and they disagree. The objective is the
accurate one. *(I previously said the Abstract didn't need this fix — that was true of the
earlier draft; the rewritten Abstract does need it.)*

**Fix.** Abstract → "A bring-your-own-model evaluator, configurable at runtime against any
OpenAI-compatible endpoint, generates…". §3.3 → replace the first sentence with the wording
already drafted in the insertion pack (E.1).

### 1.2 The Abstract ends twice, and is 230 words against a 150-word brief

It reaches its conclusion — *"The platform demonstrates the feasibility of combining
deterministic assessment with AI-assisted feedback, although…"* — and then starts a new
topic with the fine-tuned generator sentence. The insert landed after the closing sentence
instead of before it.

**Fix.** Move the generator sentence to sit before *"The platform demonstrates…"*, and cut
to 150 words. See Part 3 for a rewritten Abstract at length.

### 1.3 The Conclusion contains two conclusions

Section 9 runs the team's conclusion ("This project developed 4ALL…") and then a second one
("This project set out to determine whether…"). Both open with *This project*, both
summarise the whole system, and the seam is obvious. The second also introduces the
recommender's 99.7% figure for the first time in a conclusion, which is where new numbers
should not appear.

**Fix.** One conclusion. Part 3 gives a merged version.

### 1.4 The Discussion says the same thing twice about the recommender

*"The recommender component provides a foundation for adaptive learning, but its
effectiveness depends on the quality of its training data and evaluation design. A decision
tree is suitable for an initial prototype because its rules can be inspected…"* is
immediately followed by *"The recommender demonstrates that a simple, fully interpretable
classifier is sufficient…"*. The first hedges, the second asserts, and they cover identical
ground.

**Fix.** Delete the earlier paragraph; the later one is stronger and better evidenced.

### 1.5 Table of Contents is stale

It lists 3.1–3.4 and 4.1–4.3. The body has **3.5** and **4.4**. It also predates the
Ethics/Limitations/Discussion/Future Work/Conclusion numbering.

### 1.6 §4.2 contradicts itself

Headline: **13/15 (86.7%)**. Four sentences later: *"did not change the overall accuracy
(12-13 out of 15)"*. Pick one, or state plainly that the figure varied by run — the
run-to-run drift is real and documented, and saying so is stronger than hiding it.

### 1.7 Leftover placeholder

*"Graph of the performance"* is still sitting in §4.2 as body text.

### 1.8 Two figures share a label

The Appendix has **"Figure 4.y: Decision Tree"** and **"Figure 4.y: Feature Importance"**.
The second is 4.z.

### 1.9 Figures are in an appendix but cited as inline figures

§4.3 says "(Figure 4.x)", "(Figure 4.y)", "(Figure 4.z)" as though they are on the page.
Either move them inline — they are the evidence for the paragraphs that cite them — or
relabel as Appendix Figures A1–A3 and adjust the citations. **Inline is better**: the depth
sweep and the tree are among the strongest evidence in the report, and burying them weakens
the Results section the rubric weighs heavily.

### 1.10 Title page date precedes the work it describes

*August 12, 2026*, while the References carry *"Retrieved August 17, 2026"* and §4.4 reports
experiments run 13–16 August.

### 1.11 Eight references are never cited in the text

APA requires every reference-list entry to appear in text. Uncited: **Bito (2025)**,
**Cohen (1960)** (only appeared in the optional human-rating paragraph, which was not
included), **Hui et al. (2024)**, **Python Software Foundation**, **scikit-learn
developers**, **Thangaraj (2025)**, **Ultra Lab (2026)**, **Xia et al. (2025)**.

This is directly assessed ("correct citation of sources"). Two options per entry: cite it or
cut it. Four are easy to cite and worth citing —

- **Thangaraj (2025)** → §2, the uncited claim about adaptive formative assessment.
- **Xia et al. (2025)** → §3.1, first mention of LeetCodeDataset.
- **Hui et al. (2024)** → §3.5, first mention of Qwen2.5-Coder.
- **Bito (2025)** or **Ultra Lab (2026)** → §1.1, the manual-review and cost claims.

Cut Cohen, Python Software Foundation and scikit-learn developers unless cited.

### 1.12 The Ethics section is the weakest in the report, and it is separately assessed

Sections 5.1–5.6 are written entirely in the conditional — *may*, *should*, *may be
necessary* — and contain **no citations** and **no findings from this project**. Every other
section is evidence-led. This one reads as generic AI-ethics material that would fit any
system.

The sharpest example: §5.2 says the recommender *"may produce unfair recommendations if its
training data contains inaccurate or unbalanced assumptions"*. The report already
establishes something stronger and specific — the training data is **synthetic**, the labels
come from a **hand-written policy**, and the most influential feature is an efficiency score
from a model with a **measured blind spot** (2 of 15). Ethics is discussing a hypothetical
while Results and Limitations document the real thing three pages later.

**Fix.** Rewrite ethics against this project's own evidence, and cite. Part 3 supplies a
version, including the automated-progression paragraph.

---

## Part 2 — Structure against the brief

| Brief requires | Present? |
|---|---|
| Title page | Yes |
| Abstract (150 words) | Yes, but 230 words |
| Introduction | Yes |
| Background | Yes |
| Methodology | Yes (as "Methods") |
| **Implementation** | **Missing** |
| Results & Evaluation | Yes |
| Ethical Considerations | Yes, but see 1.12 |
| **Limitations & Future Work** | Split, with Discussion between them |
| Conclusion | Yes, doubled |
| References | Yes, 8 uncited |
| **AI Use Declaration appendix** | **Missing — and it is applicable** |

**Two real gaps.**

*Implementation.* The brief separates *Methodology* ("data, AI techniques, system design")
from *Implementation* ("key design decisions and how the system was built"). Cheapest fix
that costs no words: retitle §3 **"Methodology and Implementation"** and add one sentence to
its opening saying it covers both. The material is already there — §3.2's subprocess design,
§3.3's defensive parser, §3.5's execution-based test values are all implementation
decisions.

*AI Use Declaration.* The brief says "if applicable". You fine-tuned a model and used AI
tooling in development — it is applicable, and omitting it on a rubric line that names it is
an avoidable loss. Draft is in the insertion pack (C.11), and it needs a sentence from each
member.

**One ordering problem.** Limitations (6) → Discussion (7) → Future Work (8) puts Discussion
between two halves of what the brief treats as one section. Merge to **6. Limitations and
Future Work**, then **7. Discussion**, then **8. Conclusion**.

---

## Part 3 — The cut plan

### First: confirm the spacing assumption

At 12pt double-spaced, a page is ~250 words, so 6–10 pages is **1,500–2,500 words** and your
draft (~7,900) needs a **71% cut**. If the brief does not actually mandate double spacing,
single-spacing makes it ~500 words/page and the budget becomes **3,000–5,000 words** — a 45%
cut instead of 71%. **Check this before cutting anything**, because it is the difference
between a trim and an amputation.

The plan below targets **2,400 words**, the double-spaced worst case.

### The principle: cut generic prose, protect measured findings

The rubric names *"depth of evaluation and critical reflection on results and limitations"*
and *"quality of the ethics and fairness analysis"*. Your specific, uncomfortable findings —
the tautological accuracy, the retrain that did not help, the harness-configuration
artefacts, the model that never once produced self-consistent tests — are exactly what those
lines reward, and no other team will have them. **Protect those. Cut the material that could
have been written before the project started.**

### Per-section budget

| Section | Now | Target | What goes |
|---|---|---|---|
| Abstract | 230 | **150** | Rewritten below |
| 1 Introduction | 1,020 | **300** | §1.1 and §2 duplicate each other heavily; §1.4 restates §1.2. Keep the problem, the objectives, one significance sentence. |
| 2 Background | 450 | **250** | Delete what §1.1 already said; keep the fine-tuning paragraphs and add the missing citations. |
| 3.1–3.3 | 740 | **300** | Compress to one paragraph each. |
| 3.4 Recommender | 700 | **250** | Keep features, the labelling policy, grouped splitting. Cut the archetype detail and guardrail list. |
| 3.5 Generator | 700 | **250** | Keep base/method one-liner, topic-held-out split, execution-based test values. Cut prompt-sharing and deployment detail. |
| 4.1–4.2 | 450 | **200** | Keep the numbers, cut the narration. |
| 4.3 Recommender results | 600 | **250** | **Keep the tautology paragraph in full.** Cut the archetype monotonicity checks. |
| 4.4 Generator results | 520 | **250** | **Keep both tables and the measurement note.** Cut the live-session anecdote. |
| 5 Ethics | 450 | **300** | Rewrite, do not trim — see below. |
| 6 Limitations + Future Work | 850 | **300** | Merge. Future Work as one sentence listing four items, not ten bullets. |
| 7 Discussion | 750 | **200** | Delete the duplicated recommender paragraph and everything restating Results. Keep the negative finding. |
| 8 Conclusion | 500 | **150** | Merged version below. |
| | **7,960** | **~2,400** | |

### Rewritten Abstract (150 words)

> Programming assessment systems commonly give identical questions and feedback to learners
> of differing ability, while manual code review does not scale. This project presents 4ALL,
> an adaptive assessment platform combining deterministic testing, AI-assisted feedback,
> question recommendation and question generation. Submissions are screened by static
> analysis and executed in a sandboxed subprocess against a validated set of 50 Python
> problems. A bring-your-own-model evaluator, configurable against any OpenAI-compatible
> endpoint, produces conceptual hints and complexity judgements, matching 13 of 15
> hand-labelled efficiency scores. A decision-tree recommender selects the next question. A
> fine-tuned 3-billion-parameter model generates new questions in the platform's schema,
> with each test case's expected output computed by executing the model's own solution
> rather than predicted by it — raising usable generated questions from none to roughly a
> third of requests. Evaluation identifies specific limits in complexity judgement,
> recommender validation and generation reliability.

*149 words.*

### Rewritten Ethics section (~300 words)

Replaces 5.1–5.6. Evidence-led rather than conditional, and cites.

> **Privacy.** Every model-dependent component can run against a locally hosted model, in
> which case student code never leaves the machine; a cloud endpoint is a choice the user
> makes, not a dependency. Where one is used, students should be told their code is
> processed externally, and prompts should carry no identifying information.
>
> **Automated progression on an imperfect signal.** The recommender's most influential
> feature is an efficiency score produced by a language model, and that model has a measured
> blind spot: it misjudged two of fifteen calibration solutions whose inefficiency was
> concealed inside a single loop. Language-model judges carry systematic biases (Zheng et
> al., 2023). A student affected is not merely scored inaccurately — they are routed onto a
> different learning path. Two choices limit the harm: reinforcement is the conservative
> default, so noise more often costs time than advances a student beyond their competence,
> and the decision is displayed rather than applied silently.
>
> **Fairness.** Style scores must reflect structure and clarity, not the language of
> comments or the origin of variable names; the project's rating guide instructs raters
> accordingly. The risk sharpens for any future component judging written English, where a
> student who understands the material but writes in a second language could score below a
> more fluent but weaker peer.
>
> **Integrity.** Because student code enters the grading prompt, a comment could attempt to
> instruct the model. The prompt therefore treats all text inside submissions as material to
> be evaluated, never as instructions — otherwise the assessment would advantage students
> who can manipulate a language model.
>
> **Transparency and disclosure.** Deterministic test results are presented separately from
> model interpretations, and generated questions are flagged and stored apart from the
> curated bank. The error rates in §4.2–4.4 are reported plainly: presenting AI judgements
> without characterising their reliability invites more trust than the evidence supports.

### Merged Conclusion (~150 words)

> 4ALL integrates dataset normalisation, sandboxed execution, AI-assisted feedback,
> adaptive recommendation and question generation. All 50 questions and reference solutions
> passed structural and execution validation; the evaluator matched 13 of 15 efficiency
> scores; the recommender reproduced its labelling policy on held-out simulated learners;
> and the fine-tuned generator produced a verified, solvable question in roughly a third of
> requests.
>
> Two findings generalise beyond this system. First, fine-tuning taught a small model the
> structure of the question schema but could not teach it to determine what its own code
> returns — a property supplied instead by the execution environment, which converted a
> component producing nothing usable into a working one. A property a deterministic
> component can establish should not be trained. Second, both the recommender's 99.7%
> accuracy and the generator's apparent improvement after retraining proved weaker on
> inspection than they first appeared. Establishing what a measurement does not show is part
> of the result, not a caveat appended to it.

### Order of operations

1. Confirm the spacing requirement — it may halve the work.
2. Fix the four contradictions (1.1–1.4). Do this first; they cost marks regardless of
   length.
3. Apply the structural fixes: retitle §3, merge Limitations and Future Work, add the AI Use
   Declaration.
4. Cut to budget, protecting the measured findings.
5. Regenerate the Table of Contents last.
6. Cite or cut the eight orphan references.
