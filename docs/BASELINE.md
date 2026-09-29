# Milestone A: repository truth baseline

Observed 2026-09-29. Owner: AreteDriver. Scope: this repository only.

## Authority and inspected state

Local start: `5e0f3b8706b92b8923c8daa6236d0dc16d17ac08`, clean working tree,
branch `docs/treatment-experiment-contract`. GitHub main:
`fad6995d06a013e137914c6438b18dd78a8ac9f5`; latest inspected CI run
`33478558892` succeeded against that older documentation tree. No open PRs.
The local implementation commits `85c3ac2` and `5e0f3b8` are not on main.
GitHub is the canonical durable source; local features are unpublished candidates.
No push, merge, release, paid run, or live-system change is part of this run.

Reviewed: all tracked paths; package modules; tests; suites/datasets/fixtures;
three JSON schemas; scripts; CI; root documents; public replay manifest;
historical results; triage UI and extracted pattern notes; local Git history;
GitHub default-branch tree, commits, CI definition, runs and open PR collection.
Generated build/cache directories are non-authoritative.

## Current-state map and contradictions

| Area | Evidence / state at start | Reconciliation |
|---|---|---|
| Engine | CURRENT local consumer of external `evalcore==0.2.0` | Retain dependency and existing suite API; no second task runner |
| Suites | CURRENT 10 structured-response and 8 finding-quality cases | Replay proves fixture behavior only |
| Evidence | PARTIAL non-overwriting writers and per-artifact hashes | Not signed, not tamper-proof, not independent reproduction |
| Schemas | PARTIAL three schemas; runtime performs selected checks | Repository validator only checked schema dialect; public schema omitted supported `target` mode |
| CI | CURRENT local tests/lint/replay; hosted CI only older validation | Do not cite hosted green checks as validation of this candidate |
| Current reality | STATUS.md already serves current-state role | Reuse, remove stale manual test count, label unpublished state |
| Architecture | README diagram includes calibrated judges | Label judge branch PLANNED; introduce focused architecture authority |
| Roadmap | Old finish line excludes new project audit scope | Preserve live-evidence gate separately from A–B acceptance |
| Standards | No adopted organization standard or manifest in repo | Adopt existing owner standards with provenance and explicit bounded automation profile |
| Agent readiness | No AGENTS.md or canonical source index | Add minimal entry point, commands, boundaries, stop conditions |
| Historical sources | v1 finding fixtures retained; heuristic note refers to superseded engine roadmap | Keep evidence; label superseded note DEPRECATED |
| Tests | Existing unittest suite and replay integration tests | Record fresh baseline separately; coverage percentage UNKNOWN |
| Safety | Secret exclusions exist; no security authority | Document trusted legacy runners versus untrusted read-only audit |

Known pre-existing weaknesses: HTTP adapter blocks its async caller and reads an
unbounded response; existing bundle readers assume trusted local paths and
selected manifest fields; reviewer strings are attribution, not authenticated
approval. Legacy live/publication commands must not ingest hostile bundles.
These are explicit release-hardening follow-ups, not evidence of an exposed
credential or a regression caused by A–B. A–B certification does not certify
those execution paths as safe for untrusted inputs.

## Adopted source standards

The two files under `docs/standards/` are unmodified snapshots of owner-maintained
v1.0 standards (2026-06-18), discovered in
`AreteDriver/Argus_Overview` under those same filenames. No central standards
repository was found in this project's sources; this origin is recorded rather
than invented. Their checksums are recorded in `standards-provenance.json`.

The standards require seven hard gates, human orientation/contradiction/cold-agent
reviews and classification-specific weighted scores. Automated presence checks
cannot honestly supply the latter. The A–B automation profile must return
`PASS WITH CONDITIONS` when its deterministic gates pass but manual certification
remains unperformed; score and full certification remain UNKNOWN. It must fail
on deterministic blockers. This is a documented partial implementation of the
existing standard, not a redefinition of full PASS.

## Smallest implementation plan

1. Adopt source standards and document existing truth, weaknesses and ownership.
2. Add a strict versioned project manifest and package its JSON Schema.
3. Add `project audit` with bounded reads, path/symlink restrictions, fixed Git
   probes, source references and hashes, age checks and explicit claim checks.
   Manifest commands are descriptive data and are never executed by the audit.
4. Reuse STATUS/METHODOLOGY/ROADMAP; map document roles with justified aliases.
5. Prove malformed, conflicting, stale and hostile projects fail; exercise the
   real CLI and installed wheel. Add repeatable CI evidence and acceptance gates.
6. Record self-audit limitations and the next Work Receipts milestone. Stop at B.

## Acceptance gate

PASS for bounded Milestone A: clean starting tree; fresh pinned dependency
installation; 30/30 tests; repository validation (2 suites, 18 cases, 3 schema
headers, 1 public bundle); Ruff check and format. See
[evidence/milestone-a.json](evidence/milestone-a.json). Coverage is UNKNOWN.
No existing test regression was observed. Identified risks are recorded above.
Machine-specific cache stalls were environmental; fresh dependencies and a
separate cache completed. The Apple Git license issue was avoided with the
already-installed bundled Git, without changing system configuration.
