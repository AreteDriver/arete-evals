# Finish roadmap

The repository is an eval-suite consumer, not an engine-consolidation project.
Work that does not improve suite validity, reproducibility, or public evidence
is outside the v1 finish line.

## Completed

- [x] Resolve the `evalcore` namespace ambiguity by deliberately adopting and
  exact-pinning the external `evalcore==0.2.0` engine.
- [x] Add versioned cases and executable expected outcomes.
- [x] Add replay and live target adapter boundaries.
- [x] Replace serialized-output regexes with parsed-object contract grading.
- [x] Add known-good and known-bad fixtures, including false-positive controls.
- [x] Add suite, treatment, private-manifest, and public-manifest validation.
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
2. Freeze the v1 cases and holdout before looking at the candidate results.
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
