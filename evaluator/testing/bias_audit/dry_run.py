import json
from evaluator.grading import evaluate_complexity
from evaluator.testing.bias_audit.variants import BIAS_AUDIT_SET

question = {"question_id": "audit_dry_run", "description_md": "See code"}
config = {"provider": "ollama", "model": "gemma2"}

REPETITIONS = 3
DRY_RUN_SOLUTIONS = BIAS_AUDIT_SET[:2]  # just the first 2 for the dry run

results = []

for solution in DRY_RUN_SOLUTIONS:
    base_id = solution["base_id"]
    for variant_name, code in solution["variants"].items():
        for rep in range(REPETITIONS):
            print(f"{base_id} / {variant_name} / rep {rep + 1}...")
            result = evaluate_complexity(code, question, config)
            results.append(
                {
                    "base_id": base_id,
                    "variant": variant_name,
                    "repetition": rep + 1,
                    "efficiency_score": result.efficiency_score,
                    "style_score": result.style_score,
                    "big_o_time": result.big_o_time,
                    "raw_feedback": result.raw_feedback,
                }
            )

with open("evaluator/testing/bias_audit/dry_run_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nDry run complete: {len(results)} evaluations saved.")
