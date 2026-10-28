# Arete Evals agent guide

Owner: AreteDriver. Reviewed: 2026-09-29.
<!-- arete:package_version=0.2.0 -->
<!-- arete:engine_version=0.2.0 -->

Read PROJECT_MANIFEST.yaml, STATUS.md, ARCHITECTURE.md, ROADMAP.md,
METHODOLOGY.md, SECURITY.md and docs/PROJECT_AUDIT.md before substantial work.
The manifest maps document roles; STATUS is current state, ROADMAP future work.
GitHub AreteDriver/arete-evals main is durable authority; local changes are
candidates until reviewed and published. See docs/BASELINE.md for divergence.

Purpose: provide evidence that AI-generated work meets claimed requirements.
Keep suite execution in external evalcore. No routing, orchestration, model
hosting, resource management, portfolio database or project manager here.

## Commands

Use a clean virtual environment, then `python -m pip install -r requirements-ci.txt`
and `python -m pip install --no-deps --no-build-isolation -e .`.

- Tests: `python -m unittest discover -s tests -v`
- Lint: `ruff check arete_evals tests scripts`
- Format: `ruff format --check arete_evals tests scripts`
- Suites: `python scripts/validate_repo.py`
- Project: `arete-evals project audit .`
- Acceptance evidence: `python scripts/verify_project.py --out /tmp/arete-evidence`
- Wheel: `python -m pip wheel --no-deps --no-build-isolation . -w /tmp/arete-wheel`

Manifest commands are discovery data. Review repository code before running it.
For imported or hostile repositories, use only read-only audit in isolation.

## Rules

Preserve historical evidence. Do not edit runs/public or results to make a gate
pass. Do not modify sibling repositories, production or live systems. No paid
model calls, credential changes, publishing or merge without task authorization.
Follow SECURITY.md. Add adversarial tests for behavior changes and reconcile
claims in the canonical documents. Run tests, lint, suite validation, project
audit and evidence reproduction before committing a milestone. Report UNKNOWN
for missing evidence; passing deterministic checks is not full certification.

Stop on failed blocking gates, material authority conflicts or scope expansion.
Current bounded scope is Milestone C: Work Receipts and bounded integrity evidence.
Read docs/WORK_RECEIPTS.md for its contract. Packs, routing and external integrations
remain deferred; a valid receipt does not authorize external actions.
