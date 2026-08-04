import time
from evaluator.grading import evaluate_complexity
from evaluator.testing.golden_set.golden_set import GOLDEN_SET

config = {"provider": "ollama", "model": "gemma2"}
question = {"description_md": "See code"}

times = []
for entry in GOLDEN_SET:
    start = time.time()
    evaluate_complexity(entry["code"], question, config)
    elapsed = time.time() - start
    times.append(elapsed)
    print(f"{entry['id']}: {elapsed:.1f}s")

print(f"\nMin: {min(times):.1f}s")
print(f"Max: {max(times):.1f}s")
print(f"Average: {sum(times) / len(times):.1f}s")
