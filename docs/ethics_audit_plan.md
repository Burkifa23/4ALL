# Linguistic Bias Audit Plan

## Purpose
Test whether the grading prompt scores functionally identical code
differently based on surface-level linguistic features (variable/comment
language, phrasing style) rather than actual logic or efficiency.

## Method
Take ~8 solutions from the golden set. For each, create 4 variants that
are byte-for-byte equivalent in *behavior* (same logic, same output),
differing only in:

  (a) Native-idiomatic English identifiers and comments
  (b) Non-native-style phrasing/grammar in comments
  (c) Transliterated/non-English identifiers (e.g. Spanish, Twi, Hindi
      romanized variable names)
  (d) No comments at all

## Measurement
For each of the 8 solutions × 4 variants, run through evaluate_complexity()
on both providers (Ollama and OpenAI, if available). Record:
  - efficiency_score (should NOT move — logic is identical)
  - style_score (differences here are the actual signal to watch)
  - raw_feedback text (qualitative tone check)

## Analysis
  - Compute mean score delta per variant class vs. the (a) baseline.
  - Flag any mean gap ≥ 0.5 as a finding worth reporting.
  - Qualitative pass: does feedback language sound harsher, more
    dismissive, or more generous for any variant class?

## Citable reference
Jadhav, R., Danve, J., & Shaw, S. (2026, March 19). Implicit grading bias in large language models: How writing style affects automated assessment across math, programming, and essay tasks. arXiv.org. https://arxiv.org/abs/2603.18765

How language bias persists in scientific publishing despite AI tools. (2026, July 14). Stanford Graduate School of Education. https://ed.stanford.edu/news/how-language-bias-persists-scientific-publishing-despite-ai-tools