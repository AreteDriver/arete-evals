# Evaluation methodology

**Version:** 1.0
**Scope:** Design, execution, calibration, retention, and publication rules for
`arete-evals` suites.

## 1. Evidence boundary

An engine with passing self-tests proves engine behavior. A suite replaying
known-good and known-bad fixtures proves metric behavior on those fixtures. A
run against a documented public-project revision proves only what that run,
dataset, target, and configuration observed.

The repository does not use “production” as a synonym for “real.” Claims name
the exact public project, revision, model, prompt, dataset, and run artifact.

## 2. Suite lifecycle

Each suite moves through four evidence states:

1. **Designed:** cases, expected outcomes, graders, and thresholds exist.
2. **Replay-validated:** known-good controls pass and seeded defects fail.
3. **Target-validated:** the frozen suite has run against a named target with
   complete provenance.
4. **Calibrated:** human review measures grader agreement on a held-out sample.

Only states 2–4 are runnable evidence. State 4 is required before an LLM judge
can become a release-blocking metric.

## 3. Case and dataset rules

- Cases have stable IDs and live under a versioned dataset directory.
- `input` describes what the adapter sends to the target.
- `expected` contains machine-enforced outcome constraints.
- Case changes require a dataset-version change unless they are formatting
  only; content hashes independently detect silent edits.
- Calibration cases and holdout cases remain separate. Do not tune a grader on
  its holdout failures and report the same holdout as independent evidence.
- Each important failure mode needs at least one known-bad fixture and one
  nearby known-good control.

## 4. Grading order

Use the least subjective valid measure:

1. Parsed schema and type checks.
2. Deterministic case-specific invariants.
3. Aggregate classification or regression metrics.
4. Calibrated rubric graders.
5. Open-ended judges only for exploratory analysis.

Fail-fast checks are appropriate for unambiguous contract violations. They
must have adversarial tests proving both detection and non-detection behavior.

The v1 structured-response grader operates on a decoded object. Regex is used
only to identify a key/value shape inside the already-decoded rationale; it is
not used to parse JSON.

The v2 context-hygiene grader compares exact expected and predicted finding
sets. It reports true positives, false positives, and false negatives through
per-category and aggregate precision, recall, and F1. Empty expected sets are
explicit negative controls: an empty prediction scores perfectly, while any
reported finding reduces precision and fails the exact contract.

## 5. Replay and live execution

Replay and live modes use the same cases and graders.

- **Replay:** deterministic CI path; no credentials, network, or model calls.
- **Live:** adapter invokes a named public-project target. A target revision and
  exact model identifiers are mandatory.

A controlled treatment comparison may use the same target revision for both
arms. In that design the differing analysis mode, model, and prompt identifiers
must remain explicit in the variant metadata; a shared revision must not be
presented as a code-change comparison.

Model-generated outputs are stochastic. A live comparison sets sample count,
ordering, timeout, retry policy, and maximum spend before execution. Treatment
order is randomized per case when order could bias the result.

## 6. Run-record contract

Every canonical private bundle retains:

- full, untruncated model output;
- per-case and aggregate scores;
- suite and dataset versions plus content hashes;
- exact engine version;
- target revision;
- exact model and prompt identifiers;
- treatment metadata and SHA-256 fingerprint;
- latency, tokens, cost, retries, and errors when available;
- artifact sizes and SHA-256 checksums.

The bundle directory is non-overwritable. Corrections produce a new bundle and
link back to the superseded record; they do not mutate historical evidence.

## 7. Metric validation

Metric quality is reported separately from target quality.

- **False positive:** known-good output fails.
- **False negative:** seeded known-bad output passes.
- **Target failure:** target output violates a validated metric.
- **Infrastructure error:** the adapter, provider, or environment fails before
  a valid output can be graded.

“No false negatives” may be claimed only for an identified labeled fixture set
that contains known-bad examples. It is never inferred from a set containing
only passing outputs.

## 8. Comparison and uncertainty

Baseline and candidate comparisons are paired by case and sample. Reports show
raw per-case outcomes, effect size, variance, and uncertainty—not only a mean
score.

For stochastic or judge-scored suites:

- use repeated samples;
- pre-register a minimum meaningful improvement;
- report paired confidence intervals;
- account for correlated cases through slicing or clustered resampling;
- treat an interval spanning zero as inconclusive.

The 10-case v1 replay is a deterministic regression test and does not claim
population-level statistical significance.

## 9. Judge calibration

An LLM judge remains advisory until:

1. the rubric and judge prompt are versioned;
2. outputs are blind-rated by humans;
3. judge/human agreement, error, and disagreement slices are reported;
4. acceptance thresholds are fixed before the target comparison.

Judge model, temperature, reasoning configuration, and replayed judgments are
part of provenance.

## 10. Privacy and publication

Full outputs are private by default. Public artifacts are derived through an
explicit command requiring reviewer attribution.

- Default public export contains response hashes and sizes, not response text.
- Full output requires the `--include-outputs` flag after manual review.
- Credentials are read only from named environment variables and are never
  serialized.
- Public artifacts must not contain secrets, private user data, employer data,
  or machine-specific paths.
- Retention is not automatically indefinite: private records follow the data
  owner’s policy; public records are retained only while their evidence value
  and publication basis remain valid.

## 11. Historical BenchGoblins artifact

The 2026-05-22 run remains evidence of a metric false-positive investigation.
Its outputs are 500-character prefixes and its model/suite provenance is
incomplete. It is therefore historical evidence, not a canonical v1 run.

The current adversarial replay independently covers the failure family with
known-bad JSON leaks and known-good ordinary uses of “recommendations.”
