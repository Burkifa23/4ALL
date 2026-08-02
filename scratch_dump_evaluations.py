import json
from evaluator.grading import evaluate_complexity
from evaluator.testing.golden_set.golden_set import GOLDEN_SET

config = {"provider": "ollama", "model": "gemma2"}
question = {"description_md": "See code"}

dumps = []
for entry in GOLDEN_SET:
    result = evaluate_complexity(entry["code"], question, config)
    dumps.append(result)

with open("evaluator/testing/sample_evaluations.json", "w") as f:
    json.dump(dumps, f, indent=2)

print(f"Dumped {len(dumps)} evaluations to evaluator/testing/sample_evaluations.json")

import time

dumps = []
for entry in GOLDEN_SET:
    result = evaluate_complexity(entry["code"], question, config)
    dumps.append(result)
    time.sleep(2)
