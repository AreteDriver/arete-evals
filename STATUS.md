# Project status

| Attribute | Current state |
|---|---|
| Status | **RUNNABLE OFFLINE; LIVE EVIDENCE PENDING** |
| Last verified | 2026-09-03 |
| Suite package | `arete-evals-suite==0.2.0` |
| Engine | External `evalcore==0.2.0`, exact-pinned |
| Canonical suites | `structured-response-integrity@v1`; `deep-analysis-finding-quality@v2` |
| Versioned cases | 18 |
| Automated tests | 30 |
| Canonical replay | Both suites pass their frozen replay comparisons |
| Public-project target | `AreteDriver/context-hygiene` selected and fast arm smoke-tested |
| Live public-project run | Full fast/deep comparison not yet executed |

## Working now

- Clean-checkout installation through `pip install -e .`.
- Complete replay coverage for baseline and candidate variants.
- Parsed structured-response grading with case-specific expected outcomes.
- Adversarial fixtures covering the historical leak and false-positive shape.
- Live HTTP adapter with environment-only credentials, bounded timeouts, and
  retry classification.
- Isolated `context-hygiene` CLI adapter with frozen fast/deep treatments,
  provider token/retry limits, and structured precision/recall/F1 grading.
- Exact finding contracts plus clean and adversarial near-misses that penalize
  false positives instead of rewarding over-reporting.
- Immutable private bundles with full outputs, suite/dataset hashes, exact
  engine version, treatment fingerprints, and artifact checksums.
- Human-attributed public export that defaults to hashes instead of output.
- CI validation, tests, replay execution, and bundle assertions.

## Honest limitations

- No canonical fast/deep bundle has been produced with model credentials yet.
- The public target does not calculate currency cost; the live protocol uses
  token/request bounds plus a provider-side budget ceiling.
- No calibrated LLM judge is enabled; v1 uses deterministic graders only.
- The replay datasets are focused 10-case and 8-case regression suites, not a
  broad model benchmark.
- The committed public replay is based on curated adversarial fixtures, not
  production traffic.
- The historical BenchGoblins record contains truncated output prefixes and
  incomplete provenance. It is excluded from canonical v1 claims.

## Definition of v1 complete

V1 becomes complete when the committed `context-hygiene` suite is run against
one exact public target revision with its frozen fast and deep treatments,
complete private outputs, a reviewed public derivative, an approved spend
ceiling, and a second-person blinded review of a sample.

## Scope

This is independent public project work. It demonstrates evaluation practice
and evidence discipline; it is not presented as employer production ownership,
an industry benchmark, or a standalone evaluation platform.
