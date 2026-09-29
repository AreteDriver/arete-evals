# Architecture authority

Owner: AreteDriver. Reviewed: 2026-09-29. Scope: local candidate implementation.
<!-- arete:package_version=0.2.0 -->
<!-- arete:engine_version=0.2.0 -->

## CURRENT

Python 3.11+ package `arete-evals-suite`. CLI entry point `arete_evals.cli:main`.
Two independent evaluation paths share a package, not a new orchestration layer:

1. Existing suites → adapters → external evalcore engine → deterministic graders
   → private run bundles → human-attributed public derivatives. `validation.py`
   performs suite-specific checks; `bundles.py` writes and `publication.py`
   exports. Existing root `schemas/` describe legacy run contracts.
2. Project manifest → packaged JSON Schema → `project.py` bounded deterministic
   checks → text or JSON report with input SHA-256, Git revision and conditions.
   No target Python imports, manifest-command execution, networking, writes to
   the audited target, model calls or approval policy. The schema ships inside
   the wheel under `arete_evals/schemas/`; the repository does not duplicate it.

The project audit reads at most 1 MiB per input, refuses symlink components and
traversal, bounds YAML nesting, rejects aliases/duplicates/custom tags, and runs
only fixed read-only Git probes with a timeout. Run against a frozen checkout;
this is not a sandbox against another process changing parent directories during
inspection. Auditor dependencies and Git executable must be trusted.

## Authority and boundaries

Arete Evals owns verification, acceptance evidence and regressions. The existing
engine remains external and exact-pinned. Supervisor owns routing, budget and
stopping decisions; Forgehand owns execution/retries/resources; Conduit owns
transport; GitHub owns durable source/history and CI enforcement. No integration
with those three systems is implemented here. CLI JSON is local evidence, not
an approved cross-repository transport protocol.

No server or deployment topology: local CLI plus GitHub Actions. The browser
triage tool is a manually opened historical-results viewer. Live adapters require
explicit trusted targets and credentials; offline project audit needs neither.

## PARTIAL and PLANNED

Project-folder standard automation is PARTIAL: exact annotated claim checking
and file evidence cannot establish semantic truth, full safety or human readiness.
Full certification is UNKNOWN. Read `docs/PROJECT_AUDIT.md` for exact guarantees.
Legacy artifact schema enforcement and hostile-bundle ingestion are PARTIAL.
Work receipts, trust progression, eval packs, comparisons across workers and
integration contracts are PLANNED in ROADMAP; calibrated judges are PLANNED.

## Decisions (2026-09-29)

- Adopt the existing owner standards unchanged; use a documented deterministic
  profile instead of pretending to implement the weighted human rubric. Reverse
  only when evidence-backed manual assessment can be bound to an exact snapshot.
- Reuse STATUS as current-state authority, ROADMAP as prioritized backlog and
  METHODOLOGY as testing strategy. Manifest role notes explain these aliases;
  separate placeholder files would create drift without additional information.
- Use JSON Schema with one direct pinned dependency (`jsonschema`) instead of
  hand-maintaining a second manifest type system. Package the schema in the wheel.
- Restrict v1 to data inspection. A manifest command is never execution authority.
  Any future runner needs a separate explicit trust design outside this audit.
