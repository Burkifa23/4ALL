# Day 5 Baseline — Grading Prompt V1

Model: gemma2 (local, via Ollama)
Golden set size: 15 entries

## Parsing results
- Valid JSON on first try / retry / fallback: not separately instrumented yet — all 15 runs returned a parseable big_o_time (no "unknown" fallbacks triggered)

## Accuracy vs. golden labels
- Efficiency-score exact match: 13/15

## Per-entry results
| Entry | Got eff | Expected eff | Got Big-O | Expected Big-O | Match |
|---|---|---|---|---|---|
| two_sum_brute | 1 | 1 | O(N^2) | O(N^2) | ✅ |
| two_sum_decent | 3 | 3 | O(N log N) | O(N log N) | ✅ |
| two_sum_optimal | 5 | 5 | O(N) | O(N) | ✅ |
| valid_parens_brute | 3 | 1 | O(N) | O(N^2) | ❌ |
| valid_parens_decent | 5 | 5 | O(N) | O(N) | ✅ |
| valid_parens_optimal | 5 | 5 | O(N) | O(N) | ✅ |
| reverse_string_brute | 5 | 1 | O(N) | O(N^2) | ❌ |
| reverse_string_decent | 5 | 5 | O(N) | O(N) | ✅ |
| reverse_string_optimal | 5 | 5 | O(N) | O(N) | ✅ |
| find_max_brute | 1 | 1 | O(N^2) | O(N^2) | ✅ |
| find_max_decent | 5 | 5 | O(N) | O(N) | ✅ |
| find_max_optimal | 5 | 5 | O(N) | O(N) | ✅ |
| check_duplicates_brute | 1 | 1 | O(N^2) | O(N^2) | ✅ |
| check_duplicates_decent | 3 | 3 | O(N log N) | O(N log N) | ✅ |
| check_duplicates_optimal | 5 | 5 | O(N) | O(N) | ✅ |

## Notes
- Both misses were brute-force solutions the model misjudged as efficient:
  `valid_parens_brute` (repeated string `.replace()` in a loop — actually
  O(N^2)) and `reverse_string_brute` (string concatenation in a loop —
  actually O(N^2)). In both cases the model likely pattern-matched on
  "single for loop" and missed that operations *inside* the loop
  (string replace, string concat) are themselves O(N), making the
  true complexity O(N^2).
- All "decent"/"optimal" tier solutions were scored perfectly — the
  model is more reliable on genuinely efficient code than on spotting
  hidden inefficiency inside brute-force code.
- No fallback/unknown results — parser handled all 15 outputs cleanly
  on the first pass.
- Next iteration (Week 11 Day 2) should add a Few-Shot example
  specifically covering "single loop but O(N^2) due to what's inside
  it" to sharpen this blind spot.