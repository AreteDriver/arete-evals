# Agent Work Receipts v1

Owner: AreteDriver. Reviewed: 2026-10-27. Status: CURRENT local candidate.

A receipt records what a producer reports happened during one bounded task. It
is evidence about a particular run or artifact, never a permanent rating of a
model. This implementation captures and checks records; it does not execute work,
route models, retry tasks or grant approval.

## Commands

```
arete-evals receipt finalize draft.json --out receipt.json
arete-evals receipt verify receipt.json --artifacts-root evidence/
arete-evals receipt verify receipt.json --artifacts-root evidence/ --expected-sha256 <digest>
arete-evals receipt render receipt.json
```

Start from `fixtures/work-receipt-unknown-v1.json`, a documentation example with
explicit unknowns, not evidence of an actual task. Supply only observed facts.
`finalize` validates the draft and writes a new finalized JSON envelope using
exclusive creation and mode 0600. Existing files and symlink destinations are
never overwritten. Its exit 0 means a valid receipt was written, not successful
work. `render` checks envelope integrity before displaying the record; it does
not read artifact files. Rendered null means UNKNOWN; empty arrays mean the
producer reports observing none. False and zero are known values, not unknowns.

`verify` returns exit 0 only if all declared artifacts match and a declared
subject artifact is bound. The result is PASS WITH CONDITIONS, never work
acceptance. Missing artifacts, mismatched hashes/sizes, unsafe paths or malformed
receipts fail (exit 1). Missing artifact root, no artifacts or no subject produce
UNKNOWN and exit 1. A caller-supplied expected digest must also match. Usage errors
exit 2. Errors do not echo untrusted values. Unexpected crashes remain nonzero.

## Machine contracts and compatibility

`arete_evals/schemas/work-receipt-v1.schema.json` defines both
`agent-work-receipt-v1` drafts and `finalized-work-receipt-v1` envelopes.
`receipt-verification-v1.schema.json` defines verification results. Both ship in
the wheel. Unknown fields/versions, missing required fields and invalid types fail.
Breaking changes require a new version; no implicit upgrades or migrations.
Existing suite, project-audit and bundle CLI interfaces remain available.

Every draft contains:

- Task ID, agent/model, repository, starting and ending revisions.
- Inspected/modified files and tests added; null when unavailable.
- Test commands as data, reported outcomes/counts and evidence references.
- Evaluation outcomes, scope violations, regressions and security findings.
- Retries, human intervention count, tokens, elapsed seconds and cost/currency.
- Producer/time/method/run provenance; optional confidence with an explicit basis.
- Human-review requirement and an explicit subject artifact.
- Relative artifact paths, stable IDs, byte sizes and SHA-256 digests.

The repository is a credential-free HTTPS identifier. Revisions are full SHA-1
or SHA-256 object IDs, or null. Artifact references must resolve to unique IDs.
Reported test PASS requires nonzero passes, zero failures/errors/skips and an
evidence reference. Evaluation PASS also requires evidence. These consistency
rules do not authenticate the producer or prove the evidence content is true.
Unknown outcomes and telemetry must not be filled using model confidence.

## Integrity and evidence strength

The receipt digest covers the entire draft, including provenance and referenced
artifact digests. `arete-json-v1` means Python JSON encoding with sorted object keys,
compact separators, ASCII escaping, finite numbers only and no Unicode
normalization. Arrays keep their order. It is not RFC 8785. Transport finalized
bytes unchanged; a different producer must implement these encoding rules.
Finalized files use a self-contained envelope and require no database or service.

| Strength | Checked evidence | Does not guarantee |
|---|---|---|
| RECORDED | Schema, semantic consistency and envelope self-digest | Artifact availability, true claims or origin |
| CONTENT_CHECKED | All nonempty declared artifact bytes match | Authentic producer, correct tests or subject relevance |
| ANCHORED_CONTENT | Content checked, subject bound, digest matches caller's external expectation | Independent reproduction, human approval or work acceptance |

A failed artifact check still returns FAIL regardless of its record's integrity.
An attacker can edit a receipt and recompute its self-digest. Only an expected
digest retained through a separately trusted channel detects that substitution.
The verifier cannot establish whether that channel is trustworthy; a digest taken
from the same untrusted envelope adds no independent assurance. Checksums are not
signatures, filesystem immutability, or human authorization. Changing files later
requires re-verification. Partial writes are invalid; rerun to a new destination.

`authenticity`, `work_acceptance`, `independent_reproduction` and `human_approval`
always remain UNKNOWN in v1. `human_review_required: false` is only the producer's
stated requirement, not evidence of approval. No trust is attached to the model.
METHODOLOGY's Designed / Replay-validated / Target-validated / Calibrated lifecycle
continues to describe suite quality; receipt integrity does not promote a suite
into those states. Full artifact certification is PARTIAL pending independently
validated run/approval attestations, not an implemented L0–L5 ladder.

## Safe input boundary

JSON only, no executable tags or commands. Reject duplicate keys, nonfinite
numbers, excessive nesting, extra fields and control characters. Limits: 1 MiB
per input/artifact, 20 nesting levels, 100 artifacts, 16 MiB aggregate artifacts,
1,000 file references per file-list. Paths must be canonical and relative;
traversal, symlinks, nonregular files and sensitive paths are rejected. Inputs
are data: no project imports, subprocess calls, network access or environment
capture by the receipt library. The output parent and the supplied artifact root
are caller-selected. Use frozen files; this is not a sandbox against concurrent
filesystem mutation. Review all metadata before sharing: no automatic secret
redaction is promised, and deliberate producer text can still contain secrets.

The new reader reuses bounded path/file checks from project audit. It does not
reuse legacy bundle ingestion, whose restrictions remain in SECURITY.md.

## Dogfooding and CI

`scripts/verify_project.py` now emits `receipt.json`, `receipt.txt`, its draft and
`receipt-verification.json` alongside the acceptance manifest and logs. The receipt
covers the **fixed verification run**, not the preceding agent implementation.
Its subject is the acceptance manifest, which contains exact source hashes and
command outcomes. Observed test counts, changed files during verification,
starting/ending revisions and elapsed time are recorded. Model, cost, tokens,
human interventions, tests added and security/regression findings stay null when
not measured. `verifier-observed` names the producer method; it does not mean the
run occurred on GitHub. CI uploads these files through its existing artifact step.

Receipt errors fail the acceptance process. A failed test run still gets a valid
receipt of failure; validating that receipt must not turn the failed run into PASS.
Review-generated files are local until the corresponding GitHub revision runs.

## Deferred

Authenticated producer identities, independent reproduction, signed human
approval, broader trust promotion, external transport adapters, model comparisons,
evaluation packs and routing/orchestration remain outside this bounded milestone.
