# Implementation change log

## 22 October 2026 — v0.1 reliability milestone

- Added explicit protection against external hostnames resolving to private, loopback, link-local, or reserved addresses.
- Made the dashboard identify keyword-only results when semantic analysis is unavailable, preventing the score from being represented as a hybrid score.
- Added a regression test for private DNS resolution.
- Verified the Python test suite after the change.

The WordPress deployment, analytics, and course research tasks remain pending.
