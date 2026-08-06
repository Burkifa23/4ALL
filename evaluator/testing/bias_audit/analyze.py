import json
from collections import defaultdict

with open("evaluator/testing/bias_audit/dry_run_results.json") as f:
    results = json.load(f)

# Group by variant class, average across solutions and repetitions
by_variant = defaultdict(list)
for r in results:
    by_variant[r["variant"]].append(r["style_score"])

baseline_key = "a_native_english"
baseline_mean = sum(by_variant[baseline_key]) / len(by_variant[baseline_key])

print("=== Style Score Deltas vs. Native English Baseline ===\n")
for variant, scores in by_variant.items():
    mean_score = sum(scores) / len(scores)
    delta = mean_score - baseline_mean
    flag = " ⚠️ FLAG (≥0.5 gap)" if abs(delta) >= 0.5 and variant != baseline_key else ""
    print(f"{variant}: mean={mean_score:.2f}, delta vs baseline={delta:+.2f}{flag}")

# Also check efficiency scores didn't move (they shouldn't — same logic)
print("\n=== Efficiency Score Check (should be identical across variants) ===\n")
by_variant_eff = defaultdict(list)
for r in results:
    by_variant_eff[r["variant"]].append(r["efficiency_score"])

for variant, scores in by_variant_eff.items():
    print(f"{variant}: scores={scores}")
