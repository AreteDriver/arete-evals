# Execution roadmap

<!-- arete:package_version=0.2.0 -->
<!-- arete:engine_version=0.2.0 -->

The repository is an eval-suite consumer, not an engine-consolidation project.
Project verification adds a bounded acceptance path alongside the existing
suite evidence work; neither path owns execution or model routing.

## Current milestone A–B and prioritized backlog

1. A: reconcile repository truth, record baseline and adopted standards.
2. B: implement manifest and read-only audit; test malformed/hostile projects;
   reconcile docs; run deterministic self-audit and repeatable CI evidence.
3. Review A–B evidence and perform the source standard's required manual reviews.
   Hosted/local publication remains a separate gate through a reviewed PR.
4. C (PLANNED): Work Receipts schema, explicit unknown telemetry and integrity
   tests. See docs/PROJECT_AUDIT.md for the next bounded run.
5. D–F (PLANNED): composable packs, model/agent outcome comparisons, then clean
   Forgehand/Conduit/Supervisor contracts. No implementation in A–B.

A–B acceptance: tests without skips, lint/format, both replay suites, safe-input
fixtures, packaged schema and deterministic self-audit pass; evidence records
unknowns and no unrelated changes. Full certification is pending human gates.
Blockers: unpublished local implementation and outstanding manual review.
Owner: AreteDriver. Review by 2026-11-24 (56-day active-project policy).
Pause when no funded/current objective exists; preserve evidence and document
resume conditions. Archive only with final disposition and successor recorded.

## Existing suite work completed locally

- [x] Resolve the `evalcore` namespace ambiguity by deliberately adopting and
  exact-pinning the external `evalcore==0.2.0` engine.
- [x] Add versioned cases and executable expected outcomes.
- [x] Add replay and live target adapter boundaries.
- [x] Replace serialized-output regexes with parsed-object contract grading.
- [x] Add known-good and known-bad fixtures, including false-positive controls.
- [x] Add exact finding contracts, negative controls, and precision/recall/F1
  grading for the context-hygiene v2 dataset.
- [x] Add suite/treatment checks and selected manifest/checksum validation
  (full legacy runtime schema enforcement remains partial).
- [x] Add immutable evidence bundles with complete outputs and checksums.
- [x] Add review-gated public export and harden triage rendering.
- [x] Add unit, adapter, integration, immutability, and publication tests.
- [x] Publish a hashes-only canonical offline replay report.

## Remaining v1 gate: canonical public-project evidence

Selected target: public `AreteDriver/context-hygiene`. The baseline is its
deterministic fast mode and the candidate is its Anthropic-backed deep mode;
both intentionally run the same target revision.

1. Commit the target-side usage/limit metadata, pin that exact revision, and
   approve the provider-side maximum spend.
2. Freeze the v2 cases and holdout before looking at the candidate results.
3. Run baseline and candidate with repeated samples appropriate to model
   variance and retain the complete private bundle.
4. Recompute aggregate metrics from per-case scores and inspect every failure.
5. Blind-review a sample with a second person.
6. Publish a sanitized derivative with reviewer attribution and precise
   limitations.

Exit criterion: the seeded defect is caught in replay, the documented public
baseline/candidate result is reproducible, and no claim exceeds that evidence.

## Deferred to v0.2

- Bare agent vs skill vs skill+MCP treatment experiment.
- Calibrated LLM-judge graders and judge/human agreement gates.
- Additional domain suites and larger holdouts.
- Automated case harvesting, which must never bypass human approval.
- Drift/SPC plugins and fleet-wide consolidation.

These are useful only after the first canonical live evidence bundle exists.
