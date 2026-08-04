"""Feature definitions — the single source of truth for the recommender.

Both training (`recommender.train`) and serving (`recommender.engine`) encode
through `vector_to_row()`. Nothing else is allowed to compute feature math;
copy-pasted encoding is how train/serve skew gets in.

FEATURE DEFINITIONS (mirrored in docs/recommender_design.md)
------------------------------------------------------------
question_difficulty   int 1-3, straight from the question metadata. Ordinal,
                      used as-is: a Decision Tree splits on thresholds, so
                      Easy<Med<Hard survives without an OrdinalEncoder.
question_topic        one-hot over the frozen TOPICS tuple below. Unknown
                      topic -> all-zeros row (no crash, no silent reindex).
attempts_on_question  submissions on THIS question this session, INCLUDING the
                      one just judged. The app appends to history on submit and
                      only then recommends, so this is >=1 at every real
                      decision point and 0 only at cold start.
user_pass_rate        passes / attempts over the WHOLE session so far,
                      including the attempt just judged. Denominator is
                      attempts, not questions.
avg_efficiency_score  mean LLM efficiency over every scored attempt this
                      session (session-wide, not last-N).
avg_style_score       same, for style.
last_efficiency_score efficiency of the most recent scored attempt.
last_style_score      style of the most recent scored attempt.

COLD-START DEFAULTS (no history at all)
---------------------------------------
user_pass_rate 0.5, avg_efficiency_score 3.0, avg_style_score 3.0,
last_efficiency_score 3, last_style_score 3, attempts_on_question 0.
0.5 and 3 are deliberate mid-scale values: a fresh student is neither assumed
competent nor assumed struggling. 0.0 would have made every new student look
like a failing one and biased the first recommendation toward "reinforce".
"""

import numpy as np

from contracts.types import FeatureVector

# Frozen with the model. Do NOT derive this from data/questions at import time:
# that folder is gitignored and can change, and a shifted one-hot column order
# would silently corrupt a model trained against the old order.
TOPICS = (
    "Array",
    "Bit Manipulation",
    "Dynamic Programming",
    "Geometry",
    "Graph",
    "Greedy",
    "Hash Table",
    "Math",
    "Memoization",
    "Queue",
    "Recursion",
    "Sorting",
    "Stack",
    "String",
    "Tree",
    "Two Pointers",
    "Union Find",
)

NUMERIC_FEATURES = (
    "question_difficulty",
    "attempts_on_question",
    "user_pass_rate",
    "avg_efficiency_score",
    "avg_style_score",
    "last_efficiency_score",
    "last_style_score",
)

FEATURE_NAMES = NUMERIC_FEATURES + tuple(f"topic={t}" for t in TOPICS)

COLD_START = {
    "attempts_on_question": 0,
    "user_pass_rate": 0.5,
    "avg_efficiency_score": 3.0,
    "avg_style_score": 3.0,
    "last_efficiency_score": 3,
    "last_style_score": 3,
}


def vector_to_row(fv: FeatureVector) -> np.ndarray:
    """Encode one FeatureVector as a (1, len(FEATURE_NAMES)) float array.

    Column order is FEATURE_NAMES and must never change without retraining —
    tests/test_recommender.py asserts it.
    """
    numeric = [float(getattr(fv, name)) for name in NUMERIC_FEATURES]
    topics = [1.0 if fv.question_topic == t else 0.0 for t in TOPICS]
    return np.array([numeric + topics], dtype=float)


def assemble_features(history, question) -> FeatureVector:
    """Build a FeatureVector from session history + the current question.

    Person 4's runtime entry point. Pure — no streamlit, no session_state —
    so training, tests and the app all go through the same code path.

    history: list of attempt dicts, oldest first. Required keys:
        question_id  str
        result       str, "passed" counts as a pass (matches SandboxResult.status)
    Optional keys (from the LLMEvaluation of that attempt, when one was run):
        efficiency_score  int 1-5
        style_score       int 1-5
    Attempts without scores are ignored by the score averages but still count
    toward user_pass_rate and attempts_on_question, so a session of pure
    failures (which never get graded) still moves the pass rate.

    question: the question dict from data/questions/*.json (needs question_id,
        difficulty, topic).
    """
    qid = question["question_id"]

    attempts_on_question = sum(1 for a in history if a["question_id"] == qid)

    if history:
        passes = sum(1 for a in history if a["result"] == "passed")
        user_pass_rate = passes / len(history)
    else:
        user_pass_rate = COLD_START["user_pass_rate"]

    scored = [a for a in history if a.get("efficiency_score") is not None]
    if scored:
        avg_eff = sum(a["efficiency_score"] for a in scored) / len(scored)
        avg_sty = sum(a["style_score"] for a in scored) / len(scored)
        last_eff = scored[-1]["efficiency_score"]
        last_sty = scored[-1]["style_score"]
    else:
        avg_eff = COLD_START["avg_efficiency_score"]
        avg_sty = COLD_START["avg_style_score"]
        last_eff = COLD_START["last_efficiency_score"]
        last_sty = COLD_START["last_style_score"]

    return FeatureVector(
        question_id=qid,
        question_difficulty=question["difficulty"],
        question_topic=question["topic"],
        attempts_on_question=attempts_on_question,
        user_pass_rate=user_pass_rate,
        avg_efficiency_score=avg_eff,
        avg_style_score=avg_sty,
        last_efficiency_score=last_eff,
        last_style_score=last_sty,
    )
