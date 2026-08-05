"""Export the report figures and the ML-vs-rules comparison table.

    python -m recommender.figures   ->   docs/report/figures/

Everything is computed on held-out students using the same split as train.py
(same seed, same GroupShuffleSplit), so the numbers here match the numbers
train.py prints.
"""

import json
import tempfile
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.inspection import permutation_importance  # noqa: E402
from sklearn.metrics import accuracy_score, f1_score, recall_score  # noqa: E402
from sklearn.tree import plot_tree  # noqa: E402

from contracts.types import FeatureVector  # noqa: E402
from recommender import engine  # noqa: E402
from recommender.features import FEATURE_NAMES  # noqa: E402
from recommender.train import MODEL_PATH, load_dataset, split  # noqa: E402

FIGURES_DIR = Path("docs/report/figures")

# rules_baseline logs every call, and data/predictions.jsonl is the Week 13
# evaluation dataset — redirect the log so this sweep doesn't contaminate it.
engine.PREDICTION_LOG = Path(tempfile.gettempdir()) / "recommender_figures.jsonl"


def _row_to_vector(r):
    return FeatureVector(
        question_id=r.question_id,
        question_difficulty=r.question_difficulty,
        question_topic=r.question_topic,
        attempts_on_question=r.attempts_on_question,
        user_pass_rate=r.user_pass_rate,
        avg_efficiency_score=r.avg_efficiency_score,
        avg_style_score=r.avg_style_score,
        last_efficiency_score=r.last_efficiency_score,
        last_style_score=r.last_style_score,
    )


def _scores(y_true, y_pred):
    return {
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro"),
        "level_up_recall": recall_score(y_true, y_pred, pos_label="level_up"),
        "reinforce_recall": recall_score(y_true, y_pred, pos_label="reinforce"),
    }


def main():
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    bundle = joblib.load(MODEL_PATH)
    clf = bundle["model"]

    X, y, groups, df = load_dataset()
    _, test_idx = split(X, y, groups)
    X_test, y_test = X[test_idx], y[test_idx]
    test_df = df.iloc[test_idx]

    # --- figure 1: the tree itself -------------------------------------
    fig, ax = plt.subplots(figsize=(18, 9))
    plot_tree(
        clf,
        feature_names=list(FEATURE_NAMES),
        class_names=list(clf.classes_),
        filled=True,
        rounded=True,
        fontsize=9,
        ax=ax,
    )
    ax.set_title("Recommender decision tree (max_depth=3, class_weight=balanced)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "decision_tree.png", dpi=150)
    plt.close(fig)

    # --- figure 2: permutation importance ------------------------------
    imp = permutation_importance(
        clf, X_test, y_test, n_repeats=20, random_state=42, scoring="f1_macro"
    )
    order = np.argsort(imp.importances_mean)[::-1][:10]
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(
        [FEATURE_NAMES[i] for i in order][::-1],
        imp.importances_mean[order][::-1],
        xerr=imp.importances_std[order][::-1],
        color="#4c72b0",
    )
    ax.set_xlabel("drop in macro-F1 when the feature is shuffled")
    ax.set_title("Permutation importance (top 10, held-out students)")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "feature_importance.png", dpi=150)
    plt.close(fig)

    # --- figure 3: depth sweep -----------------------------------------
    sweep = bundle["depth_sweep"]
    fig, ax = plt.subplots(figsize=(7, 4))
    depths = sorted(sweep)
    ax.plot(depths, [sweep[d] for d in depths], marker="o")
    ax.axvline(clf.max_depth, ls="--", c="grey")
    ax.annotate(
        f"chosen: depth {clf.max_depth}",
        (clf.max_depth, sweep[clf.max_depth]),
        textcoords="offset points",
        xytext=(10, -14),
    )
    ax.set_xlabel("max_depth")
    ax.set_ylabel("grouped-CV macro-F1")
    ax.set_title("Depth sweep — smallest depth on the plateau wins")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "depth_sweep.png", dpi=150)
    plt.close(fig)

    # --- table: model vs rules baseline --------------------------------
    model_pred = clf.predict(X_test)
    rules_pred = np.array(
        [engine.rules_baseline(_row_to_vector(r)).decision for r in test_df.itertuples()]
    )
    comparison = {
        "decision_tree": _scores(y_test, model_pred),
        "rules_baseline": _scores(y_test, rules_pred),
        "n_test_rows": int(len(y_test)),
        "n_test_students": int(len(set(groups[test_idx]))),
    }
    (FIGURES_DIR / "comparison.json").write_text(
        json.dumps(comparison, indent=2), encoding="utf-8"
    )

    header = f"| metric | decision tree | rules baseline |\n|---|---|---|\n"
    body = "".join(
        f"| {m.replace('_', ' ')} | {comparison['decision_tree'][m]:.3f} | "
        f"{comparison['rules_baseline'][m]:.3f} |\n"
        for m in ("accuracy", "macro_f1", "level_up_recall", "reinforce_recall")
    )
    note = (
        f"\nHeld-out: {comparison['n_test_students']} students, "
        f"{comparison['n_test_rows']} decisions. Split by student "
        "(GroupShuffleSplit, seed 42) — no student appears in both sets.\n"
    )
    (FIGURES_DIR / "comparison.md").write_text(header + body + note, encoding="utf-8")

    print(header + body + note)
    print(f"figures written to {FIGURES_DIR}")


if __name__ == "__main__":
    main()
