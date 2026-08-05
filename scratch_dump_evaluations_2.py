import json
import time
from evaluator.grading import evaluate_complexity
from evaluator.testing.golden_set.golden_set import GOLDEN_SET

question = {"description_md": "See code"}
config = {"provider": "ollama", "model": "gemma2"}

dumps = []
for i, entry in enumerate(GOLDEN_SET, 1):
    print(f"{i}/{len(GOLDEN_SET)}: {entry['id']}...")
    result = evaluate_complexity(entry["code"], question, config)
    result["golden_id"] = entry["id"]
    dumps.append(result)
    time.sleep(2)

with open("evaluator/testing/sample_evaluations_batch2.json", "w") as f:
    json.dump(dumps, f, indent=2)

print(f"\nDumped {len(dumps)} evaluations to sample_evaluations_batch2.json")
