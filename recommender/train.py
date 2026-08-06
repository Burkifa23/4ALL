"""Train the DecisionTreeClassifier. Reproducible: run twice, get the same model.

Two methodological points that matter more than the hyperparameters:

GROUPED SPLITS. Rows from one simulated student are highly correlated — they
share an archetype, a running pass rate and a difficulty trajectory. A plain
train_test_split would put question 3 of a student in train and question 4 in
test, leaking the student's ability into the test set and inflating every
number. GroupShuffleSplit / GroupKFold on student_id hold out whole students.

ENCODING THROUGH features.vector_to_row. Training does not build its own
matrix from the CSV columns; it reconstructs a FeatureVector per row and calls
the same function the runtime calls. Slower, and worth it — it makes train/serve
skew a structural impossibility rather than a review checklist item.
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.tree import DecisionTreeClassifier

from contracts.types import FeatureVector
from recommender.features import FEATURE_NAMES, vector_to_row

SEED = 42
# Chosen from the depth sweep, not guessed: grouped-CV macro-F1 is 0.912 at
# depth 2 then plateaus (0.951 / 0.952 / 0.957 / 0.953 ... at depths 3-6).
# Depth 3 is the smallest depth on the plateau and the differences above it are
# fold noise, so interpretability breaks the tie.
MAX_DEPTH = 3
TEST_FRACTION = 0.25
DEPTH_SWEEP = range(2, 9)

DATA_PATH = Path("data/synthetic/logs_v1.csv")
MODEL_PATH = Path("recommender/models/decision_tree_v1.joblib")


def load_dataset(path=DATA_PATH):
    """CSV -> (X, y, groups, dataframe), encoded through vector_to_row."""
    df = pd.read_csv(path)
    rows = [
        vector_to_row(
            FeatureVector(
                question_id=r.question_id,
                question_difficulty=r.question_difficulty,
                question_topic=r.question_topic,
                attempts_on_question=r.attempts_on_question,
                last_attempt_passed=r.last_attempt_passed,
                user_pass_rate=r.user_pass_rate,
                avg_efficiency_score=r.avg_efficiency_score,
                avg_style_score=r.avg_style_score,
                last_efficiency_score=r.last_efficiency_score,
                last_style_score=r.last_style_score,
            )
        )
        for r in df.itertuples()
    ]
    X = np.vstack(rows)
    return X, df["label"].to_numpy(), df["student_id"].to_numpy(), df


def split(X, y, groups, seed=SEED):
    """Hold out whole students, never individual rows."""
    splitter = GroupShuffleSplit(n_splits=1, test_size=TEST_FRACTION, random_state=seed)
    train_idx, test_idx = next(splitter.split(X, y, groups))
    return train_idx, test_idx


def new_model(max_depth=MAX_DEPTH):
    return DecisionTreeClassifier(
        max_depth=max_depth,
        min_samples_leaf=20,
        class_weight="balanced",
        random_state=SEED,
    )


def depth_sweep(X, y, groups):
    """Grouped CV macro-F1 per depth. Pick the smallest depth on the plateau —
    an interpretable tree is a deliverable here, not just a nice-to-have."""
    cv = GroupKFold(n_splits=5)
    results = {}
    for depth in DEPTH_SWEEP:
        scores = [
            f1_score(
                y[te],
                new_model(depth).fit(X[tr], y[tr]).predict(X[te]),
                average="macro",
            )
            for tr, te in cv.split(X, y, groups)
        ]
        results[depth] = float(np.mean(scores))
    return results


def main():
    X, y, groups, df = load_dataset()
    train_idx, test_idx = split(X, y, groups)
    print(
        f"{len(df)} rows, {df.student_id.nunique()} students -> "
        f"{len(train_idx)} train rows / {len(test_idx)} test rows "
        f"({len(set(groups[test_idx]))} held-out students)"
    )

    clf = new_model().fit(X[train_idx], y[train_idx])
    preds = clf.predict(X[test_idx])

    print("\n=== held-out students ===")
    report = classification_report(y[test_idx], preds, digits=3)
    print(report)
    print("confusion matrix (rows=true, cols=pred, order=%s)" % list(clf.classes_))
    print(confusion_matrix(y[test_idx], preds, labels=clf.classes_))

    sweep = depth_sweep(X, y, groups)
    print("\n=== grouped-CV macro-F1 by max_depth ===")
    for depth, score in sweep.items():
        marker = "  <- chosen" if depth == MAX_DEPTH else ""
        print(f"  depth {depth}: {score:.3f}{marker}")

    metrics = classification_report(y[test_idx], preds, output_dict=True)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": clf,
            # Stored so engine.py can refuse to serve a model whose columns no
            # longer match features.FEATURE_NAMES, instead of silently
            # predicting on misaligned inputs.
            "feature_names": FEATURE_NAMES,
            "trained_on": str(DATA_PATH),
            "n_train_rows": int(len(train_idx)),
            "metrics": metrics,
            "depth_sweep": sweep,
        },
        MODEL_PATH,
    )
    print(f"\nsaved {MODEL_PATH}")
    print(
        "level_up recall: %.3f (acceptance threshold ~0.70)"
        % metrics["level_up"]["recall"]
    )


if __name__ == "__main__":
    main()
