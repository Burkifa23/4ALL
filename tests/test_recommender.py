"""Recommender checks. Plain asserts, no framework: `python tests/test_recommender.py`.

The assemble_features section is the train/serve parity artifact: Person 4 runs
this to prove their runtime feature assembly agrees with the definitions the
model was trained on, field by field.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contracts.types import FeatureVector  # noqa: E402
from recommender import assemble_features, recommend_next, rules_baseline  # noqa: E402
from recommender.engine import pick_question, question_index  # noqa: E402
from recommender.features import COLD_START, FEATURE_NAMES, vector_to_row  # noqa: E402
from recommender.labeling import label  # noqa: E402

QUESTION = {"question_id": "q_0001", "difficulty": 1, "topic": "Array"}


def vec(**kwargs):
    base = dict(
        question_id="q_0001",
        question_difficulty=1,
        question_topic="Array",
        attempts_on_question=1,
        user_pass_rate=0.5,
        avg_efficiency_score=3.0,
        avg_style_score=3.0,
        last_efficiency_score=3,
        last_style_score=3,
    )
    base.update(kwargs)
    return FeatureVector(**base)


def test_labeling():
    # branch 1: quick pass with efficient code
    assert label(True, 2, 4, 0.0) == "level_up"
    assert label(True, 3, 5, 0.0) == "reinforce"  # too many attempts
    assert label(True, 1, 3, 0.0) == "reinforce"  # efficiency below bar
    # branch 2: steady performer who laboured on this one
    assert label(True, 4, 3, 0.80) == "level_up"
    assert label(True, 4, 3, 0.70) == "reinforce"  # pass rate below bar
    assert label(True, 4, 1, 0.90) == "reinforce"  # brute force never promotes
    # failure always reinforces, whatever else is true
    assert label(False, 1, 5, 0.99) == "reinforce"


def test_vector_to_row():
    row = vector_to_row(vec())
    assert row.shape == (1, len(FEATURE_NAMES)), row.shape
    # Column order is frozen with the trained model; drift here silently
    # corrupts every prediction, so pin the first and last columns explicitly.
    assert FEATURE_NAMES[0] == "question_difficulty"
    assert FEATURE_NAMES[6] == "last_style_score"
    assert FEATURE_NAMES[7] == "topic=Array"
    assert row[0][7] == 1.0 and row[0][8] == 0.0  # one-hot lands in the right slot
    # unknown topic must not crash or shift columns
    unknown = vector_to_row(vec(question_topic="Quantum Basket Weaving"))
    assert unknown.shape == row.shape
    assert unknown[0][7:].sum() == 0.0


def test_assemble_features_cold_start():
    fv = assemble_features([], QUESTION)
    assert fv.question_id == "q_0001"
    assert fv.question_difficulty == 1
    assert fv.question_topic == "Array"
    assert fv.attempts_on_question == 0
    assert fv.user_pass_rate == COLD_START["user_pass_rate"] == 0.5
    assert fv.avg_efficiency_score == 3.0
    assert fv.avg_style_score == 3.0
    assert fv.last_efficiency_score == 3
    assert fv.last_style_score == 3


def test_assemble_features_canned_history():
    """PARITY CHECK — Person 4's assembler must produce exactly this vector.

    Session: failed q_0002 once (no LLM score, the app only grades passes),
    passed q_0002 on the second try (eff 5, style 4), then two submissions on
    q_0001 with the second passing (eff 3, style 2). History includes the
    just-judged attempt, because add_attempt fires before the recommendation.
    """
    history = [
        {"question_id": "q_0002", "result": "failed"},
        {"question_id": "q_0002", "result": "passed",
         "efficiency_score": 5, "style_score": 4},
        {"question_id": "q_0001", "result": "failed"},
        {"question_id": "q_0001", "result": "passed",
         "efficiency_score": 3, "style_score": 2},
    ]
    fv = assemble_features(history, QUESTION)
    assert fv.attempts_on_question == 2, fv.attempts_on_question  # both q_0001 rows
    assert fv.user_pass_rate == 0.5, fv.user_pass_rate  # 2 passes / 4 attempts
    assert fv.avg_efficiency_score == 4.0, fv.avg_efficiency_score  # (5+3)/2
    assert fv.avg_style_score == 3.0, fv.avg_style_score  # (4+2)/2
    assert fv.last_efficiency_score == 3
    assert fv.last_style_score == 2


def test_assemble_features_ignores_missing_scores():
    """Works before Person 4 records efficiency/style, and after."""
    history = [{"question_id": "q_0001", "result": "passed"}]
    fv = assemble_features(history, QUESTION)
    assert fv.user_pass_rate == 1.0
    assert fv.avg_efficiency_score == 3.0  # falls back to cold start
    assert fv.attempts_on_question == 1


def test_question_index():
    index = question_index()
    assert set(index) == {1, 2, 3}, set(index)
    assert all(index[d] for d in index)
    # nearest-difficulty fallback when the target level is exhausted
    exhausted = set(index[3])
    assert pick_question(3, exhausted) in index[2]


def test_recommend_next_behaviour():
    ace = vec(
        question_difficulty=1,
        attempts_on_question=1,
        user_pass_rate=0.95,
        avg_efficiency_score=4.8,
        avg_style_score=4.5,
        last_efficiency_score=5,
        last_style_score=5,
    )
    struggler = vec(
        question_difficulty=2,
        attempts_on_question=4,
        user_pass_rate=0.2,
        avg_efficiency_score=1.5,
        avg_style_score=2.0,
        last_efficiency_score=1,
        last_style_score=2,
    )
    assert recommend_next(ace).decision == "level_up"
    assert recommend_next(struggler).decision == "reinforce"

    rec = recommend_next(ace)
    assert 0.0 <= rec.confidence <= 1.0
    # guardrails
    assert rec.next_question_id != ace.question_id
    assert rec.next_question_id in question_index()[2]  # level_up from Easy -> Medium
    served = {"q_0001", "q_0021"}
    assert recommend_next(ace, exclude=served).next_question_id not in served


def test_cold_start_recommendation():
    """No history: a fresh student should not be thrown at a Hard question."""
    fv = assemble_features([], QUESTION)
    rec = recommend_next(fv)
    assert rec.decision in ("reinforce", "level_up")
    assert rec.next_question_id != fv.question_id


def test_rules_baseline():
    first_try = vec(attempts_on_question=1, last_efficiency_score=4)
    laboured = vec(attempts_on_question=3, last_efficiency_score=4)
    assert rules_baseline(first_try).decision == "level_up"
    assert rules_baseline(laboured).decision == "reinforce"
    assert rules_baseline(first_try).next_question_id != first_try.question_id


if __name__ == "__main__":
    # data/predictions.jsonl is the Week 13 evaluation dataset — don't let a
    # test run inject synthetic rows into it.
    import tempfile

    from recommender import engine

    engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_test_preds.jsonl"

    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("\nall checks passed")
