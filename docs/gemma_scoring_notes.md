# Gemma Scoring Behavior Notes (for Person 3)

Model: gemma2 (local via Ollama)

- V1 (Day 5 baseline): 13/15 exact match. Missed valid_parens_brute
  and reverse_string_brute — both brute-force solutions with hidden
  O(N^2) complexity inside a single loop, misjudged as O(N).
- V2 (added explicit rubric rule + 3rd Few-Shot example targeting
  hidden complexity): 13/15 exact match. Fixed reverse_string_brute,
  but introduced a new miss on find_max_decent (a genuinely optimal
  single-loop solution incorrectly flagged as suboptimal).
  valid_parens_brute remained unfixed.
- V3 (added explicit step-by-step reasoning instructions before
  scoring): 12/15 exact match — a regression. Fixed
  reverse_string_brute (same as V2), but now flags BOTH
  find_max_decent and find_max_optimal as suboptimal, despite
  find_max_optimal being correct in every prior version. The
  stronger "scrutinize every loop" instruction made the model
  generally over-suspicious of loops rather than more precise.
- Decision: reverted to V2. It's the best-performing version tested
  (tied with V1 on raw accuracy, but fixes a real blind spot without
  the V3 regression). valid_parens_brute remains an open, documented
  limitation.
- Recommendation for simulator jitter: ±0-1 for most solution types;
  treat "hidden complexity" and loop-heavy edge cases as an
  unreliable category rather than modeling as pure random jitter.
- Latency: some requests exceed 90s locally; recommend the app
  account for slow local inference.

  ## Batch 2 dump (Day 4) — run-to-run drift observed

   Same V2 prompt, same golden set, different run: 12/15 exact match
   (vs. 13/15 on the original baseline run). two_sum_decent and
   find_max_decent — both previously correct — drifted to wrong
   scores this time, while valid_parens_brute remained a consistent
   miss across all runs.

   Takeaway for Person 3: even beyond the known blind spots, expect
   some run-to-run score drift on 1-2 solutions per batch, even at
   temperature 0.2. Treat ±1 efficiency_score jitter as normal
   background noise, separate from the specific hidden-complexity
   blind spot.