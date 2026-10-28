# Milestones A–B verification report

Observed 2026-09-29. Scope: Arete Evals only. Local candidate; not published.

## Outcome

Milestone A baseline: 30 tests passed; two suites/18 cases validated; Ruff passed.
Milestone B: 62 tests, zero failures/errors/skips; deterministic project gates
pass. Full certification remains UNKNOWN and the standard outcome is PASS WITH
CONDITIONS pending its required human reviews. No weighted score is fabricated.

## Architecture and changed areas

- `arete_evals/project.py`: independent read-only project verification path.
- `arete_evals/cli.py`: `project audit`, JSON/text, fixed date, cleanliness and strict modes.
- `arete_evals/schemas/`: packaged manifest and report contracts; pinned standard digest.
- `PROJECT_MANIFEST.yaml`: role discovery, boundaries, canonical source, review policy,
  commands-as-data and verifiable package/engine claims.
- `tests/test_project.py`, `tests/test_acceptance.py`, fixture recipes: invalid,
  conflicting, stale, oversized, aliased, symlinked, sensitive and hostile inputs;
  provenance, determinism, CLI behavior; failed/skipped test evidence.
- `scripts/test_report.py`, `scripts/verify_project.py`: fixed trusted acceptance
  commands, count-aware test results, source snapshots before/after verification,
  artifact hashes and non-overwriting output directories.
- CI: acceptance evidence, installed-wheel smoke check, both canonical replays,
  downloadable artifacts even on failure. All action references are pinned.
- Canonical docs: STATUS retained as current authority; architecture, instructions,
  security and audit contract added; README/ROADMAP reconciled; obsolete heuristic
  port proposal explicitly deprecated; treatment target inconsistency corrected.
- Existing schema validation now checks schema validity, not just dialect strings;
  public-run schema recognizes the already-supported `target` adapter mode.

## Commands and evidence

Run in a clean environment installed from requirements-ci.txt, using Python 3.12:

```
python -m unittest discover -s tests -q
ruff check arete_evals tests scripts
ruff format --check arete_evals tests scripts
python scripts/validate_repo.py
python scripts/verify_fix.py
python scripts/verify_project.py --out /tmp/arete-evidence --as-of 2026-09-29
arete-evals project audit . --format json --as-of 2026-09-29
```

Acceptance checks passed. Suite validation reports 2 suites, 18 cases, 5 valid
schemas and one checksummed public bundle; historical pattern verification finds
0/20 hits on retained prefixes (not a false-negative measurement). Both replay
comparison contracts pass in the integration tests. Two fixed-date audit reports
were byte-identical. Wheel build and console invocation from outside the source
tree passed, proving packaged-schema discovery. The source checkout's older
retained fixture files exhibited filesystem read delays; a temporary Git checkout
plus the exact candidate changes also passed the acceptance script. Evidence
manifests record revision, dirty state, every nonignored source hash, actual
runtime versions, command outcomes and whether source changed during checks.

Full certification `--strict` intentionally exits 1. Deterministic audit exits 0
only with its explicit conditions; `--require-clean` rejects uncommitted changes.
Do not reinterpret either result as approval to merge, publish or deploy.

## Remaining risks and deliberate deferrals

- Hosted main is still `fad6995`; its green CI covers the older tree. New CI is
  configured locally but has not run on GitHub. No push or live-system changes.
- Manual orientation/cold-agent, semantic contradiction, security content review
  and weighted classification assessment remain outstanding. No production claim.
- Existing live HTTP and legacy bundle readers still have the limitations recorded
  in SECURITY and BASELINE. Audit safety does not certify those separate paths.
- Cross-platform CI execution and coverage percentage remain unverified.
- Evidence hashes are integrity checks, not signatures or independent reproduction.
- Receipts, trust levels, eval packs, model comparisons and integration contracts
  are deliberately deferred. No orchestrator or routing policy was introduced.
- The local n8n map draft is documentation only; synchronization remains pending.

## Next bounded run

Review this foundation and reconcile the unpublished implementation through a PR.
Then implement Milestone C only: a schema-validated Agent Work Receipt with explicit
unknown telemetry, exact source/run identity, test outcomes and integrity checks.
First resolve the legacy artifact-ingestion trust boundary if receipts will reuse
those readers. Add tamper/failure fixtures and bind review to a frozen artifact.
No model-routing or worker orchestration belongs in that run.
