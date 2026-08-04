"""Runtime: turn a FeatureVector into a concrete next question.

Person 4 calls recommend_next(); everything else here is support.

Deliberately free of streamlit. ui.question_loader.load_questions is decorated
with @st.cache_data, so importing it would drag streamlit into training runs
and the test script. The 8-line loader below is the cheaper trade.

Set RECOMMENDER_MODE=baseline to force the rules path — the A/B switch for
demos, and the fallback if the model ever misbehaves in front of an audience.
"""

import collections
import json
import os
from dataclasses import asdict
from pathlib import Path

import joblib

from contracts.types import FeatureVector, Recommendation
from recommender.features import FEATURE_NAMES, vector_to_row

QUESTIONS_DIR = Path("data/questions")
MODEL_PATH = Path("recommender/models/decision_tree_v1.joblib")
PREDICTION_LOG = Path("data/predictions.jsonl")
MAX_DIFFICULTY = 3

_model = None
_index = None


def _load_questions():
    """difficulty -> [question_id], built from Person 1's question files."""
    index = collections.defaultdict(list)
    for path in sorted(QUESTIONS_DIR.glob("q_*.json")):
        q = json.loads(path.read_text(encoding="utf-8"))
        index[q["difficulty"]].append(q["question_id"])
    return dict(index)


def question_index():
    global _index
    if _index is None:
        _index = _load_questions()
    return _index


def load_model():
    """Cached at module level — joblib.load on every submission would be silly.

    Returns None when no model file exists, which makes recommend_next fall
    back to the rules baseline instead of crashing a fresh clone.
    """
    global _model
    if _model is None and MODEL_PATH.exists():
        bundle = joblib.load(MODEL_PATH)
        if tuple(bundle["feature_names"]) != tuple(FEATURE_NAMES):
            raise RuntimeError(
                "Model was trained on different feature columns than "
                "features.FEATURE_NAMES defines. Retrain with "
                "`python -m recommender.train` before serving."
            )
        _model = bundle["model"]
    return _model


def pick_question(target_difficulty, exclude):
    """First candidate at the target difficulty, else the nearest difficulty.

    Topic is deliberately not a constraint: 10 of the 17 topics in the question
    set have exactly one question, so topic-matched selection would fall back
    on nearly every call anyway. Difficulty is the axis that actually carries
    the adaptive signal.
    """
    index = question_index()
    # target first, then nearest difficulties outward
    order = sorted(index, key=lambda d: (abs(d - target_difficulty), d))
    for difficulty in order:
        for qid in index[difficulty]:
            if qid not in exclude:
                return qid
    return None


def rules_baseline(vector: FeatureVector, exclude=()) -> Recommendation:
    """The if/else gate the ML classifier is measured against.

    Kept genuinely reasonable rather than a strawman — "passed this question on
    the first try" is what a sensible person would write, and the claim that a
    classifier beats it is only worth anything if the baseline had a fair shot.
    Its weakness is not stupidity, it is brittleness: it reads one field and
    has no notion of confidence or of a student's track record.
    """
    passed_first_try = (
        vector.attempts_on_question == 1 and vector.last_efficiency_score >= 3
    )
    decision = "level_up" if passed_first_try else "reinforce"
    return _build(vector, decision, confidence=1.0, mode="baseline", exclude=exclude)


def recommend_next(vector: FeatureVector, exclude=()) -> Recommendation:
    """Model-driven next question.

    exclude: extra question_ids to skip (Person 4 passes the session's served
    questions). The current question is always excluded regardless.

    Falls back to rules_baseline when RECOMMENDER_MODE=baseline is set or when
    no trained model is on disk.
    """
    if os.environ.get("RECOMMENDER_MODE") == "baseline":
        return rules_baseline(vector, exclude)

    model = load_model()
    if model is None:
        return rules_baseline(vector, exclude)

    row = vector_to_row(vector)
    decision = model.predict(row)[0]
    proba = model.predict_proba(row)[0]
    confidence = float(proba[list(model.classes_).index(decision)])
    return _build(vector, decision, confidence, mode="model", exclude=exclude)


def _build(vector, decision, confidence, mode, exclude):
    """Map a decision to a concrete question, log it, return the contract type."""
    target = (
        min(vector.question_difficulty + 1, MAX_DIFFICULTY)
        if decision == "level_up"
        else vector.question_difficulty
    )
    # Never re-serve the question the student just worked on.
    blocked = set(exclude) | {vector.question_id}
    next_id = pick_question(target, blocked)

    if next_id is None:  # every question exhausted; repeat rather than crash
        next_id = vector.question_id
        confidence = 0.0

    recommendation = Recommendation(
        next_question_id=next_id, decision=decision, confidence=confidence
    )
    _log(vector, recommendation, mode)
    return recommendation


def _log(vector, recommendation, mode):
    """Append to data/predictions.jsonl — this file IS the Week 13 evaluation set.

    Never let logging break a live session: a full disk should not end someone's
    assessment.
    """
    try:
        PREDICTION_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "mode": mode,
            "vector": asdict(vector),
            "decision": recommendation.decision,
            "confidence": recommendation.confidence,
            "next_question_id": recommendation.next_question_id,
        }
        with PREDICTION_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass
