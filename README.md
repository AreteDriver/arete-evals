# arete-evals

**Versioned evaluation suites, target adapters, calibrated graders, and the
evidence bundles produced by running them.**

`arete-evals` is a consumer of the independently maintained
[`evalcore`](https://pypi.org/project/evalcore/) engine. It does not implement a
second harness. This repository owns the cases, expected outcomes, adapters,
graders, replay fixtures, run manifests, triage, and public evidence.

## 60-second review

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

arete-evals validate suites/structured-response-integrity.yaml
arete-evals run \
  --suite suites/structured-response-integrity.yaml \
  --out runs/private
```

The canonical offline replay seeds known regressions into the baseline and
expects the candidate to satisfy every contract:

| Variant | Contract pass rate | JSON-leak gate |
|---|---:|---:|
| Baseline adversarial fixtures | 0.30 | 0.70 |
| Candidate fixtures | 1.00 | 1.00 |

See the review-gated, hashes-only
[public replay report](runs/public/structured-response-integrity-v1-replay/report.md)
and its [manifest](runs/public/structured-response-integrity-v1-replay/manifest.json).

## What this demonstrates

- Designing versioned cases whose expected outcomes are executable rather
  than descriptive metadata.
- Separating replay from live target invocation through a narrow adapter
  contract.
- Using parsed-object checks for deterministic invariants before introducing
  an LLM judge.
- Testing metric detection power with known-good and known-bad fixtures,
  including whitespace, escaping, ordinary prose, Unicode, missing details,
  and fallback decisions.
- Retaining complete private evidence while publishing only explicitly
  reviewed derivatives.

## Current status and limitations

The v1 suite is installable, validates from a clean checkout, and reproduces
offline. It has not yet produced a new canonical run against a configured
public-project target. The committed replay proves the suite and graders can
detect seeded failures; it does not prove behavior, reliability, or scale in a
deployed system.

The historical BenchGoblins run remains a case study, not canonical v1
evidence. Its retained outputs are truncated and lack the provenance required
by the current run contract. See [Project Status](STATUS.md) and
[Methodology](METHODOLOGY.md).

## Architecture

```text
Versioned cases + expected outcomes
              │
              ▼
      Target adapter contract
        ├── replay fixtures
        └── live public-project target
              │
              ▼
       Structured output object
              │
      ┌───────┴────────┐
      ▼                ▼
Deterministic       Calibrated
graders             judge graders
      └───────┬────────┘
              ▼
 Immutable run bundle
 manifest + outputs + scores
              │
              ▼
 comparison, triage, public report
```

## Repository layout

```text
arete_evals/   consumer adapters, deterministic graders, bundle tooling
suites/        executable evalcore suite configurations
datasets/      versioned cases and expected outcomes
fixtures/      offline baseline/candidate replay data
schemas/       treatment and run-manifest contracts
runs/public/   review-gated public derivatives; full private runs are ignored
case-studies/  historical suite definitions and analysis
results/       historical run records retained with explicit limitations
tools/         local triage UI
tests/         deterministic, adapter, integration, and artifact tests
```

## Canonical suite

[`structured-response-integrity@v1`](suites/structured-response-integrity.yaml)
evaluates one failure family: a structured AI response must keep `decision`,
`rationale`, and optional `details` separate instead of serializing raw data
inside prose.

The grader emits:

- `schema_valid`
- `decision_valid`
- `rationale_valid`
- `no_serialized_json_leak`
- `details_valid`
- `contract_pass`

A metric not yet run against public-project output is a hypothesis, not a
guardrail. The historical check for a leaked `recommendations` key passed its
tests but also matched ordinary prose; the public-project run and failure
review exposed that measurement error.

Case-specific requirements such as recommendation counts and decision patterns
come from each versioned case's `expected` object.

The second canonical suite,
[`deep-analysis-finding-quality@v2`](suites/context-hygiene-deep-analysis.yaml),
targets the public
[`AreteDriver/context-hygiene`](https://github.com/AreteDriver/context-hygiene)
project. It compares that project's deterministic fast analysis with its
Anthropic-backed deep analysis on eight frozen staleness, contradiction,
deadweight, and compression cases. Four positive cases require exact findings;
four clean and adversarial near-misses penalize over-reporting. The grader emits
per-category and aggregate precision, recall, and F1. Both arms use the same
target revision; the treatment under test is analysis mode, not a code revision.

## Live target contract

The `public_project_http` adapter sends:

```json
{
  "case_id": "stable-case-id",
  "input": {"query": "..."},
  "variant": {"model": "exact-model-id", "treatment": {"...": "..."}}
}
```

The endpoint returns either the structured response directly or
`{"response": {...}}`. Before a live run, commit exact model and prompt
identifiers into the suite variants, then provide the target URL through the
environment:

```bash
export ARETE_EVAL_TARGET_URL=https://public-project.example/eval
export ARETE_EVAL_TARGET_TOKEN=...  # only when the endpoint requires it

arete-evals run \
  --suite suites/structured-response-integrity.yaml \
  --mode http \
  --revision <public-project-commit-sha> \
  --out runs/private
```

Live runs reject missing target revisions and placeholder model identifiers.
Credential values are never written to run records.

### context-hygiene target

Install `context-hygiene` from the exact public commit being evaluated and
point the suite at that executable:

```bash
export CONTEXT_HYGIENE_EXECUTABLE=/path/to/pinned/bin/ctx-hygiene
export ANTHROPIC_API_KEY=...          # candidate arm only
export CONTEXT_HYGIENE_LICENSE=...    # candidate arm only

arete-evals run \
  --suite suites/context-hygiene-deep-analysis.yaml \
  --mode target \
  --revision <context-hygiene-commit-sha> \
  --out runs/private
```

The adapter writes each case and non-secret provider configuration to an
isolated temporary directory. The frozen candidate configuration allows zero
provider retries and at most 1,024 output tokens per request. Four analyzer
passes × eight cases × three samples bounds the candidate arm at 96 provider
requests and 98,304 output tokens, before input tokens. Use a provider-side
budget limit because the repository does not compute currency cost.

## Evidence and publication

Private bundles are non-overwritable directories containing full baseline and
candidate runs, per-case scores, a comparison, a report, and a manifest with
checksums and treatment fingerprints.

Public export is a separate, human-attributed step. It excludes model output by
default:

```bash
arete-evals publish runs/private/<bundle-id> \
  --reviewed-by <reviewer-id> \
  --out runs/public
```

Use `--include-outputs` only after reviewing every response for public release.

## Historical case study

The original `benchgoblins-ask` run exposed a false-positive metric: a regex
intended to find a leaked JSON key matched the ordinary English word
“recommendations.” The corrected historical check and triage record remain
useful evidence of eval repair, but the stored 500-character prefixes cannot
establish false-negative performance.

- [Historical suite](case-studies/benchgoblins-ask/suite-v0.yaml)
- [Run record](results/benchgoblins-ask-6ea664d3.json)
- [Triage](results/benchgoblins-ask-6ea664d3.triage.md)

## Development

```bash
python scripts/validate_repo.py
python -m unittest discover -s tests -v
ruff format --check arete_evals tests scripts
ruff check arete_evals tests scripts
```

See [ROADMAP.md](ROADMAP.md) for the remaining live-evidence gate and deferred
treatment experiment.
