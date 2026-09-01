# Project Status

| Attribute | Value |
|-----------|-------|
| Status | **PARTIAL — public evaluation evidence repository** |
| Last verified | 2026-08-31 |
| Installable? | Supporting requirements only; the evaluation engine is not included |
| Re-runnable? | Not end-to-end from this repository alone |
| Documented? | README, methodology, suites, run record, and triage record |

## What works

- A public suite definition for the documented BenchGoblins Ask evaluation.
- A retained JSON run record and human-readable triage record.
- A browser-based triage helper for inspecting run records.
- A methodology that separates evaluation-framework construction from evaluation practice.

## What does not work yet

- The referenced evaluation harness is not packaged in this repository.
- There is no automated CI that reruns suites against live public projects.
- There is no hosted trend dashboard.
- The recorded result demonstrates one documented run; it is not a general performance claim.

## 60-second inspection

1. Read `results/benchgoblins-ask-6ea664d3.triage.md`.
2. Inspect `results/benchgoblins-ask-6ea664d3.json`.
3. Compare the evidence with `suites/benchgoblins-ask.yaml`.
4. Review `METHODOLOGY.md`.

## Scope

This is independent public project work. It demonstrates evaluation practice and evidence discipline; it is not presented as employer production ownership, an industry benchmark, or a standalone evaluation platform.
