# Report sections — CodeGenTutor (fine-tuned question generator)

Everything below is ready to paste. Section A says **where each piece goes and what
changes in your teammates' text**. Section B is the text itself.

---

# A. Insertion map

## A.1 Changes to text teammates have already written

| Where | Change | Why |
|---|---|---|
| **Abstract** | Insert the sentence in **B.1** after *"...recommends a subsequent question at an appropriate difficulty level."* | The abstract never mentions question generation. A reader finishes it without knowing a model was fine-tuned. |
| **1.2 Proposed solution** | Add the paragraph in **B.2** after the paragraph ending *"...through a web application."* | Custom Practice is a third capability alongside grading and recommendation, and is currently invisible. |
| **1.3 Aim and objectives** | Insert the bullet in **B.3** between the existing bullets 4 and 5 (after "Generate debugging hints…", before "Train and integrate a decision-tree classifier…") | The objectives list has eight items and none covers the fine-tune. |
| **2. Background** | Add the two paragraphs in **B.4** after the paragraph ending *"...time complexity, or coding style."* | Background needs to motivate schema-constrained generation and small-model fine-tuning. |
| **Title page date** | Change *August 12, 2026* to the submission date | The generator experiments ran 13–16 August; the current date predates the results in 4.4. |
| **4.1, final sentence** | Optional: *"...to have executable, and reproducible"* → *"to be executable and reproducible"* | Grammatical slip. |

## A.2 New sections to add

| New section | Goes | Text |
|---|---|---|
| **3.5 Fine-Tuned Question Generation** | After 3.4, end of Methods | **B.5** |
| **4.4 Question-Generator Evaluation** | After 4.3, end of Results | **B.6** |
| **5. Limitations** (additions) | Into the empty Limitations section | **B.7** |
| **6. Ethical Considerations** | New section between Limitations and Discussion; renumber Discussion to 7 | **B.8** |
| **8. Conclusion** | After Discussion | **B.9** |
| **Appendix A: AI Use Declaration** | After References | **B.10** |

## A.3 Two structural gaps against the brief

1. **The brief asks for a separate *Implementation* section** ("key design decisions and how
   the system was built"); the document has Methods but no Implementation. Either rename
   Methods to "Methodology and Implementation" and say so in the introduction, or split the
   *how it was built* material out. 3.5 below is written so it can sit in either.
2. **The brief asks for *Ethical Considerations* and a *Conclusion*.** Neither exists —
   B.8 and B.9 supply them.

---

# B. The text

## B.1 — Abstract insertion

> The platform also includes a fine-tuned question generator, produced by adapting a
> 3-billion-parameter code model so that it writes new practice questions in the
> platform's own schema, with the expected outputs of every test case computed by
> executing the model's solution in the sandbox rather than predicted by the model.

## B.2 — 1.2 Proposed solution, new paragraph

> Finally, 4ALL allows a student to request practice on a topic the fixed question bank
> does not cover. A language model fine-tuned for this purpose writes a new question in
> the same schema used by the stored questions, so that a generated question passes
> through the same sandbox, evaluator and recommender as any other. Because a small model
> cannot reliably determine what its own code returns, the expected output of each test
> case is obtained by executing the model's reference solution inside the sandbox, and any
> generated question whose tests cannot be established in this way is discarded before a
> student sees it.

## B.3 — 1.3 Objectives, new bullet

> - Fine-tune a small, locally deployable language model to generate new practice
>   questions in the platform's question schema, and establish their test cases by
>   execution rather than by model prediction.

## B.4 — 2. Background, two new paragraphs

> A related problem is the generation, rather than the assessment, of practice material.
> General-purpose language models can be prompted to write programming questions, but an
> assessment platform requires more than readable prose: it requires a machine-readable
> record whose fields the sandbox, validator and recommender can all consume. Parameter-
> efficient fine-tuning methods such as Low-Rank Adaptation (Hu et al., 2021) and its
> quantised variant QLoRA (Dettmers et al., 2023) make it feasible to adapt a model to a
> fixed output format on modest hardware, by training a small number of additional
> parameters while the original weights remain frozen and quantised. This is attractive in
> an educational setting because the resulting model is small enough to be served locally,
> which avoids both recurring API charges and the transmission of student work to an
> external provider.
>
> Fine-tuning is not, however, a general remedy. A distinction that proved central to this
> project is between properties a model can be taught by example and properties it cannot.
> The structure of an output — which fields appear, in what form — is a formatting
> behaviour that a modest number of examples can teach. Determining what a particular piece
> of Python returns for a particular input is not a formatting behaviour; it is
> interpretation, and a small model performs it unreliably regardless of how many examples
> of correct interpretation it has seen. Where a deterministic component is available to
> supply such a property, using it is preferable to attempting to train it.

## B.5 — 3.5 Fine-Tuned Question Generation *(new, end of Methods)*

> The Custom Practice feature required a model that returns a complete question record in
> the schema used by `data/questions/`, so that generated questions could be executed,
> graded and recommended by the components already described. General instruction-tuned
> models did not do this reliably, so a model was fine-tuned for the task.
>
> **Base model and method.** The base model was `Qwen2.5-Coder-3B-Instruct`, loaded in
> 4-bit precision. A code-specialised base was chosen over a general-purpose model of
> similar size because the task requires writing valid Python as well as valid JSON.
> Adaptation used QLoRA with rank 16 and scaling factor 16, applied to all seven linear
> projections of each transformer block, trained for two epochs with an effective batch
> size of eight, a learning rate of 2 × 10⁻⁴ under a linear schedule, and 8-bit AdamW. Loss
> was computed on the assistant response only, so that model capacity was not spent
> learning to reproduce the instruction it is always given. Training was performed on a
> single T4 GPU and completed in approximately two and a half hours.
>
> **Training data.** The training data is the same keep-pile described in 3.1 — the 2,599
> problems that survived compatibility filtering — rather than the stratified sample of 50
> used for the question bank. Each example pairs an instruction naming a topic and
> difficulty with a target containing the six fields the model must produce: title,
> description, starter code, entry point, reference solution and test cases. The remaining
> schema fields are bookkeeping and are filled in by the application. Critically, the split
> between training and evaluation data was made **by topic rather than at random**. A random
> split would allow the model to be evaluated on a topic it had memorised during training,
> which measures recall; holding out entire topics measures whether the model can produce a
> valid record for a topic it has never seen, which is what a student typing a free-text
> topic actually requires.
>
> **Prompt sharing.** The system prompt, the instruction format and the list of taught
> fields are defined once in `evaluator/generate.py` and imported by the training notebook.
> A model trained against one prompt and served under another is a common and difficult-to-
> diagnose failure, in which a correctly trained model appears broken. An automated test
> asserts that the system prompt stored in the Ollama Modelfile remains byte-identical to
> the one used in training.
>
> **Deployment.** After training, the adapters were merged into the base weights and
> quantised to `q4_k_m`, producing a 1.84 GB file that runs locally under llama.cpp or
> Ollama. This keeps the generator consistent with the platform's bring-your-own-model
> architecture: student code and generated questions remain on the machine.
>
> **Establishing test cases by execution.** The schema originally required the model to
> write each test case as an input together with its expected output. This asks the model
> to state, from memory, what its own reference solution returns for a given input — an
> act of interpretation rather than formatting. Measured on held-out topics, the model
> never once produced a complete set of test cases that its own solution passed (see 4.4).
>
> The final design therefore does not ask. After a generated record is parsed, the model's
> reference solution is executed in the sandbox against the model's test *inputs*, and the
> values actually returned become the expected outputs. Self-consistency then holds by
> construction for every test case whose execution succeeds. The same subprocess isolation,
> static security analysis and five-second timeout described in 3.2 apply, because
> model-written code is treated with no more trust than student-written code.
>
> Four conditions reject a generated question at this stage: a solution that does not
> execute; a test case that raises an exception; a returned value that cannot survive
> serialisation unchanged, such as a tuple, which would otherwise compare unequal when
> reloaded; and a set of computed outputs that are all identical, which would yield a
> question that a one-line stub could pass. A question surviving all four is then verified
> once more through the ordinary sandbox path before it is served.

## B.6 — 4.4 Question-Generator Evaluation *(new, end of Results)*

> The generator was evaluated on twenty held-out topics using the application's own
> acceptance checks, so that a question counted as successful only if the deployed system
> would have served it. Three measurements were recorded: whether the reply parsed as
> valid JSON, whether it contained all six taught fields, and whether the model's test
> cases were ones its own reference solution passed.
>
> **Table 4.4.1 — Schema compliance on held-out topics (n = 20)**
>
> | Metric | Base model | Fine-tuned |
> |---|---|---|
> | Valid JSON | 0/20 | 13/20 |
> | All six fields present | 0/20 | 13/20 |
> | Test cases self-consistent | 0/20 | 0/20 |
>
> The fine-tune achieved what fine-tuning can achieve. A base model that produced no usable
> record at all produced one in roughly two-thirds of attempts after training, and the two
> schema figures are identical in every condition — that is, every reply that parsed as JSON
> contained all six fields, correctly named, with the entry point matching the starter code.
> The schema was not partially learned; it was learned.
>
> Self-consistency did not move. Across every measurement of every version, the model never
> produced a complete set of test cases that its own solution passed. Inspection of failures
> showed the pattern directly: reference solutions were frequently correct, while the
> expected values disagreed with them on one or two cases — for example `got 5, expected 3`
> — indicating a model that writes working code and then misreports what that code returns.
> This is the result that motivated the execution-based design in 3.5.
>
> **Effect of the execution-based pipeline.** With expected values computed rather than
> predicted, 19 of 50 requests (38%) produced a question that passed every acceptance check
> and was served to the interface, against a raw self-consistency of zero. In a live session,
> a generated question was answered with a solution written independently of the model's own,
> using a different algorithm, and passed all eight of its test cases — evidence that the
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
> outperforming the first. That result was an artefact: the two models had been measured
> under different server context settings, one of which was returning capacity errors
> during the run. Re-measuring under identical settings removed the effect. Over the course
> of this work, three separate apparent model differences were traced to configuration
> differences in the harness rather than to the models. This is recorded because it bears
> on how the other results in this report should be read: a difference between two numbers
> is evidence about a model only when both were produced by the same harness under the same
> settings.

## B.7 — 5. Limitations, additions

> The question generator is limited by the capacity of a 3-billion-parameter model. Roughly
> a third of requests produce output that cannot be parsed, in most cases because the model
> enters a repetitive loop and emits the same fragment until it reaches the token limit. A
> decoding-level remedy was tested — a sampler penalising repeated sequences — and rejected:
> it improved parse rates but corrupted the generated Python, which contains legitimate
> repetition, reducing the proportion of parsed questions that were servable from 77% to
> 31%.
>
> The requested difficulty is not honoured. A request for a hard question typically returns
> a problem of easy or medium difficulty. This was investigated and is not a data problem:
> hard problems constituted a quarter of the training data and survived filtering at a
> higher rate than either other band. The difficulty label reaches the model as a single
> adjective competing with a topic that determines the entire problem domain, and the model
> appears to condition on the stronger signal.
>
> Computing expected values by execution guarantees that a question is solvable and
> internally consistent, but not that its tests match its written description. A model that
> writes a correct solution to a slightly different problem than the one it described
> produces a coherent and solvable exercise that does not test what it claims to. This
> failure remains detectable only by human review.
>
> The evaluation sample sizes are small. Twenty and fifty requests give standard errors of
> roughly eleven and seven percentage points respectively, which is sufficient to establish
> that the fine-tune improved schema compliance from zero, but not to separate models that
> differ by a few points. Local inference on CPU also takes between one and four minutes per
> generated question, which is acceptable for practice but would not support a class working
> simultaneously on modest hardware.

## B.8 — 6. Ethical Considerations *(new section)*

> **Privacy.** The platform's bring-your-own-model architecture allows every model-dependent
> component — hints, grading and question generation — to run against a locally hosted
> model, in which case student code is never transmitted to a third party. This was a design
> objective rather than an incidental property: a cloud endpoint is an option the user
> selects, not a default the system depends on. Where a cloud endpoint is used, the
> submitted code and the generated feedback leave the institution's control, and users
> should be informed of this before selecting one.
>
> **Fairness in automated grading.** Automated scoring of student work carries a risk of
> penalising surface characteristics rather than substance. The project's human rating guide
> explicitly instructs raters that style scores must reflect code structure and clarity, and
> must not be influenced by the language of comments, phrasing, or the linguistic origin of
> variable names. This concern applies with greater force to any component that assesses
> free-form English prose, where a student who understands the material but writes in a
> second language could be scored lower than a less capable but more fluent peer. Any future
> feature that judges written explanations should be evaluated against this risk before it
> is allowed to influence a student's progression.
>
> **Assessment integrity.** Because the grading prompt receives student code as input, a
> student could embed text in comments intended to instruct the model — for example, a
> comment asserting that the code has already been graded highly. The grading prompt
> therefore contains an explicit instruction to treat all text inside submitted code as
> material to be evaluated rather than as instructions to follow. This is an integrity
> measure as much as a security one: without it, the assessment would advantage students who
> know how to manipulate a language model.
>
> **Transparency.** Model-generated questions are recorded with a flag marking them as
> generated and are written to a separate directory from the curated question bank, so they
> cannot be mistaken for validated material or enter the recommender's evaluation pool. The
> recommender's decision is displayed in the interface rather than applied silently, so a
> student can see why a particular question was selected. Feedback produced by a language
> model is presented alongside deterministic test results, never in place of them.
>
> **Reliability and its disclosure.** The evaluation in 4.2 and 4.4 documents specific,
> reproducible weaknesses: a grading model that misjudges complexity when an expensive
> operation is nested inside a single loop, and a generator that produces a servable
> question in roughly a third of attempts. Reporting these plainly is itself an ethical
> requirement. A tool that presents AI-generated judgements to students without
> characterising their error rate invites those judgements to be trusted more than the
> evidence supports.

## B.9 — 8. Conclusion *(new section)*

> This project set out to determine whether deterministic testing, language models and
> adaptive selection could be combined into a programming assessment tool that is
> personalised, scalable and deployable without recurring cost. The resulting system
> executes submissions in an isolated sandbox, produces model-assisted feedback, recommends
> subsequent questions from measured performance, and generates new questions on demand from
> a locally hosted fine-tuned model.
>
> The most transferable finding concerns the division of labour between learned and
> deterministic components. Fine-tuning reliably taught a small model the structure of the
> platform's question schema, taking schema compliance from zero to roughly two-thirds of
> attempts on unseen topics. The same training did not, and could not, teach the model to
> determine what its own code returns — a property that remained at zero across every
> version, model size and prompt tested. Supplying that property from the execution
> environment instead of the model converted a component that produced no usable questions
> into one that produces a verified, solvable question in roughly a third of requests. The
> generalisable principle is that a property a deterministic component can establish should
> not be trained, and that identifying which properties those are is the more consequential
> design decision.

## B.10 — Appendix: AI Use Declaration

> Generative AI tools were used during the development of this project, as follows.
>
> **Within the system.** The platform is itself an application of language models. Feedback,
> grading and question generation are produced by models accessed through a configurable
> endpoint. The question generator is a model fine-tuned by the team for this project;
> training configuration, data preparation and evaluation are described in 3.5 and 4.4, and
> the notebook that produces it is included in the repository.
>
> **In development.** An AI coding assistant was used during implementation and debugging of
> the generation pipeline, the evaluation harnesses and parts of the documentation. Its use
> included diagnosing failures, drafting code, and drafting sections of this report for
> review. All measurements reported were produced by executing the described harnesses; no
> result in this report was generated or estimated by an assistant. Every figure in 4.4
> corresponds to a scorecard file committed to the repository.
>
> **Author responsibility.** The design decisions, the interpretation of results and the
> final text are the authors'. Where an assistant's initial conclusion was contradicted by
> subsequent measurement — most notably the comparison of the two training runs discussed in
> 4.4 — the corrected result is what appears here.

---

## Suggested references to add

Verify each against the published record before submission.

- Dettmers, T., Pagnoni, A., Holtzman, A., & Zettlemoyer, L. (2023). *QLoRA: Efficient
  finetuning of quantized LLMs.* arXiv:2305.14314.
- Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., & Chen, W.
  (2021). *LoRA: Low-rank adaptation of large language models.* arXiv:2106.09685.
- Hui, B., et al. (2024). *Qwen2.5-Coder technical report.* arXiv:2409.12186.
- newfacade. (n.d.). *LeetCodeDataset* [Data set]. Hugging Face.
- Gerganov, G., et al. (n.d.). *llama.cpp* [Computer software]. GitHub.
