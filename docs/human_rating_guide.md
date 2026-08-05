# Human Baseline Rating Guide

Use this guide to rate code submissions consistently. Rate BLIND — don't
look at what the LLM scored first, to avoid anchoring your judgment.

## Efficiency Score (1-5)
- 5 = Optimal time complexity for the problem
- 3 = One tier worse than optimal (e.g. O(N log N) when O(N) is possible)
- 1 = Brute force / far from optimal
- Watch for hidden complexity: a single loop containing an expensive
  operation (string concatenation, .replace(), `in` on a list) is NOT
  automatically O(N) — check what's inside the loop.

## Style Score (1-5)
- Naming clarity, code structure, idiomatic use of the language.
- Rate the code on its own merits — do not let comment language,
  phrasing style, or variable-name origin affect this score. Style
  means code structure and clarity, not linguistic background.
- Never blend with efficiency — a slow solution can still score 5 on
  style if it's clean and readable.

## Worked Examples (from the golden set)

**Example 1 — two_sum_brute**
```python
def two_sum(nums, target):
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] + nums[j] == target:
                return [i, j]
```
Efficiency: 1/5, Style: 4/5
Justification: Brute force nested loop, correct and readable, but not optimal.

**Example 2 — two_sum_optimal**
```python
def two_sum(nums, target):
    seen = {}
    for i, n in enumerate(nums):
        if target - n in seen:
            return [seen[target - n], i]
        seen[n] = i
```
Efficiency: 5/5, Style: 5/5
Justification: Optimal hashmap approach, clean and idiomatic.

**Example 3 — reverse_string_brute**
```python
def reverse_string(s):
    result = ""
    for char in s:
        result = char + result
    return result
```
Efficiency: 1/5, Style: 3/5
Justification: String concatenation in a loop is quadratic in Python since strings are immutable.

## Process
1. Read the code without looking at any existing scores.
2. Assign efficiency_score and style_score independently.
3. Write one sentence justifying each score.
4. Submit your ratings in the shared sheet/file Person 4 provides.