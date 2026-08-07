from evaluator.grading import evaluate_complexity
from evaluator.testing.golden_set.golden_set import GOLDEN_SET

config = {"provider": "ollama", "model": "gemma2"}
question = {"description_md": "See code"}

RUNS_PER_SOLUTION = 5

print("Running consistency test (5x per solution)...\n")

for entry in GOLDEN_SET:
    scores = []
    for run in range(RUNS_PER_SOLUTION):
        result = evaluate_complexity(entry["code"], question, config)
        scores.append(result.efficiency_score)

    variance = max(scores) - min(scores)
    within_1 = all(abs(s - entry["efficiency_score"]) <= 1 for s in scores)

    print(
        f"{entry['id']}: scores={scores} "
        f"(expected {entry['efficiency_score']}), "
        f"spread={variance}, within_±1_of_expected={within_1}"
    )
