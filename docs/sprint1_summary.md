# Sprint 1 Summary — Person 2 (LLM/BYOM Evaluator)

## Hint Path
- Built and adversarially tested the hint generation prompt against multiple
  broken code samples (off-by-one errors, missing return statements, typo bugs).
- Never leaked a corrected solution across the test cases tried; hints
  consistently named the specific bug location without writing the fix.
- Adapted to real question data (description_md field) with truncation for
  long descriptions.

## Grading Path
- Hand-built a 15-solution golden set (5 classic problems × 3 quality tiers:
  brute force, decent, optimal) with labeled Big-O, efficiency/style scores,
  and justifications.
- Prompt iteration history:
  - **V1** (baseline): 13/15 exact match. Missed valid_parens_brute and
    reverse_string_brute — both had hidden O(N^2) complexity inside a single
    loop, misjudged as O(N).
  - **V2** (added explicit rubric rule + 3rd Few-Shot example): still 13/15,
    but fixed reverse_string_brute while introducing a new miss on
    find_max_decent (a genuinely optimal solution flagged as suboptimal).
  - **V3** (added explicit step-by-step reasoning): regressed to 12/15 —
    over-scrutinized loops, breaking a previously-correct optimal solution
    too. Reverted to V2.
  - **Settled on V2** as the best-tested version. valid_parens_brute remains
    an unresolved, documented limitation.
- Consistency testing (5 runs per solution): most solutions scored with zero
  variance (spread=0); one showed spread=1, still within tolerance.
- A separate batch run later showed run-to-run drift even on the same V2
  prompt — two previously-correct solutions (two_sum_decent, find_max_decent)
  scored incorrectly on a different run — confirming some jitter exists
  beyond the known hidden-complexity blind spot.

## Latency
- Local Gemma grading requests on this machine: some individual requests
  exceeded 90 seconds; timeouts were raised to 150s to accommodate this.
  (Exact min/max/average from the Day 4 timing script to be filled in once
  confirmed.)

## Deliverables Sent to Person 3
- Batch 1: all 15 golden-set evaluations (single provider, Ollama/Gemma).
- Batch 2: second full run of golden-set evaluations, plus a documented note
  on run-to-run score drift for simulator jitter calibration.
- Gemma scoring behavior notes (docs/gemma_scoring_notes.md) covering
  consistency, systematic bias, and latency, for Person 3's simulator.

## Known Open Items
- optimal_complexity field is null in all sampled question files — flagged
  to Person 1; efficiency scoring is currently absolute, not relative.
- valid_parens_brute remains an unresolved scoring miss across all prompt
  versions tested.
- Sidebar's byom_config is incomplete (only stores a display-label string,
  no model/API key fields) — flagged to Person 4, pending integration.
- Live UI integration for both hint and grading paths pending a pairing
  session with Person 4.