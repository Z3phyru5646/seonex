# Implementation change log

## 22 October 2026 — v0.1 reliability milestone

- Added explicit protection against external hostnames resolving to private, loopback, link-local, or reserved addresses.
- Made the dashboard identify keyword-only results when semantic analysis is unavailable, preventing the score from being represented as a hybrid score.
- Added a regression test for private DNS resolution.
- Verified the Python test suite after the change.

The WordPress deployment, analytics, and course research tasks remain pending.

## 22 October 2026 — v0.2 and v0.3 local workflow

- Added explainable rule-based intent labels with evidence and persistent manual corrections.
- Expanded the SEONEX diagnostic to keyword, semantic, intent, title, heading, and content-overlap signals. If semantic analysis is unavailable, the UI labels the intent-aware score accordingly.
- Added evidence-led KEEP / DIFFERENTIATE / CONSOLIDATE suggestions and local human-review records. The software does not alter sites.
- Added SQLite-backed snapshots, pair matching for before/after comparisons, human labels, and binary precision/recall/F1 calculation once labels exist.
- Added tests for intent rules, recommendation boundaries, and snapshot matching.
