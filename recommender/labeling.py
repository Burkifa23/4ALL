"""The pedagogical labeling rule that generates supervised training targets.

Nobody hands you labels for "what should the next question be?", so this module
defines the policy, simulate.py generates data with it, and the classifier
learns to approximate it from noisy features.

WHY THIS ISN'T "JUST RULES WITH EXTRA STEPS"
--------------------------------------------
Fair challenge, and the honest answer is that the classifier learns *this*
labeling policy. Its value over calling `label()` directly at runtime is:

1. Degradation, not cliff-edges. `label()` needs clean `passed` / `attempts`
   / `efficiency` values. The model consumes the noisy, partial FeatureVector
   the app actually has — session averages, a jittery LLM score, sometimes no
   score at all — and still produces a decision instead of a KeyError.
2. Confidence. `predict_proba` gives a graded signal the UI can act on
   (e.g. hold difficulty when the model is 51% sure). A boolean cannot.
3. Retrainability. When Week 13 produces real labelled sessions, the policy
   improves by retraining on better data. A hand-written rule improves only by
   somebody rewriting it and re-arguing the thresholds.

The limitation belongs in Limitations, not hidden: with clean inputs the model
can at best match this rule, and any bias in the rule is inherited wholesale.
"""

LEVEL_UP = "level_up"
REINFORCE = "reinforce"


def label(passed, attempts, efficiency, user_pass_rate) -> str:
    """Mastery gate: promote only on demonstrated competence.

    Branch 1 — passed within 2 attempts AND efficiency >= 4.
        Mastery learning says advance on evidence of mastery, not on mere
        completion. Few attempts shows the student had the approach up front
        rather than converging by trial and error; high efficiency shows they
        reached a good algorithm, not just a passing one. Both together is a
        strong single-question signal, so it promotes on its own.

    Branch 2 — passed AND session pass rate >= 0.75 AND efficiency >= 3.
        Catches the steady performer this question happened to be slow on. One
        laboured question shouldn't hold back someone passing three quarters of
        the session; a sustained track record substitutes for the single-shot
        evidence branch 1 wants. Efficiency >= 3 is a floor, not a bar: it
        excludes brute force (Person 2's evaluator scores that a 1) while
        accepting merely decent code.

    Everything else reinforces, including every failure. Reinforce is the safe
    default: serving another question at the same level costs a student time,
    while promoting too early costs them the thread.
    """
    if not passed:
        return REINFORCE
    if attempts <= 2 and efficiency >= 4:
        return LEVEL_UP
    if user_pass_rate >= 0.75 and efficiency >= 3:
        return LEVEL_UP
    return REINFORCE
