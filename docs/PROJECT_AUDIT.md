# Project audit and manifest v1

Owner: AreteDriver. Reviewed: 2026-09-29.

## Adoption and document index

The adopted organization and evaluation standards are immutable reference copies
in [standards](standards/). Their origin/version/digests are in
[standards-provenance.json](standards/standards-provenance.json).
The machine authority index is [PROJECT_MANIFEST.yaml](../PROJECT_MANIFEST.yaml).
For this small active developer library, context/charter/requirements share README,
current state uses STATUS, architecture/decisions share ARCHITECTURE, execution
and backlog share ROADMAP, testing uses METHODOLOGY, instructions use AGENTS.
Role notes explain this deliberate exception to separate-file recommendations.

## Contract

`schema_version: project-manifest-v1` is mandatory. JSON Schema draft 2020-12
lives in `arete_evals/schemas/project-manifest-v1.schema.json` and is included in
the installed wheel. Unknown fields and unsupported versions fail. The accepted standard digest is
pinned in the installed schema, not chosen by the evaluated project. Empty strings,
bad dates and unsafe paths fail. YAML dates remain strings; anchors/aliases,
duplicate keys and arbitrary object tags are rejected. Metadata has explicit
owner, classification, review policy, canonical location and bounded scope.
Commands are argv arrays or null (UNKNOWN), never shell scripts to execute.
No default owner, branch, commands or certification evidence is invented.

Compatibility: existing suite/run CLI interfaces remain unchanged. Projects
without a manifest fail with a useful manifest error and may adopt v1 explicitly.
No automatic migration or silent fallback. Breaking changes get a new schema
version and validator; v1 documents remain valid under the v1 contract.

## Invocation and exit status

```
arete-evals project audit .
arete-evals project audit . --format json --as-of 2026-09-29
arete-evals project audit . --require-clean
arete-evals project audit . --strict
```

Exit 0 means deterministic gates passed (possibly with conditions), never full
certification. Exit 1 means a blocking FAIL/UNKNOWN, or incomplete certification
under `--strict`. Argparse usage errors exit 2. Unexpected evaluator crashes are
nonzero; they cannot silently become PASS. `--as-of` makes freshness reproducible;
without it, the caller's current date applies. Dirty state is a condition unless
`--require-clean` is selected. Unavailable Git provenance is blocking UNKNOWN.

## Implemented gates and limits

| Standard hard gate | Deterministic evidence | What it cannot establish |
|---|---|---|
| Identity | Required schema fields and review dates | Unique identity across portfolio |
| Boundary | Explicit scope/non-goals and safe referenced paths | Semantic coherence of every source |
| Canonical Source | Explicit repository/branch, matching origin, local Git root/revision/cleanliness | Remote synchronization or ownership authentication |
| Current Reality | Current-state authority, freshness, claim evidence files; package/engine facts derived from TOML | Truth of arbitrary capability prose or test outcomes |
| Execution Direction | Milestone, ordered actions, blockers, acceptance, test-command declaration | Whether commands succeed; never runs them |
| Source Coherence | Nonempty authority documents, standard digest, exact shared claims | Free-text contradictions, architectural quality |
| Safety and Sensitivity | Path/YAML restrictions, .env exclusion, sensitive tracked filenames | Exhaustive secret detection or runtime security |

A source claim uses exactly one `<!-- arete:key=value -->` marker per declared
document, backed by evidence paths. Values must agree with the manifest; unknown
markers fail. Supported package_version/engine_version claims are also compared
with pyproject.toml. Evidence paths and marker agreement alone do not prove any
other claim. Human semantic contradiction review remains required. Dates are
bounded by the manifest's explicit review policy; this is not inferred roadmap age.
Sources are additionally capped at 256 unique files and 16 MiB total.

Automated result vocabulary follows the source standard: `PASS WITH CONDITIONS`
or `FAIL`; findings use PASS/WARNING/FAIL/UNKNOWN. Full certification is always
UNKNOWN in v1, weighted score null, tests_executed false. The human orientation,
cold-agent, semantic, security and weighted classification reviews are not
simulated. Full PASS and QUARANTINE judgments remain outside this bounded profile.
`--strict` intentionally stays nonzero until future reviewed evidence support.

## Evidence and reproducibility

JSON is `project-audit-v1`: dated profile, outcomes, seven gate results, stable
finding codes with relative file/line references, input digests, revision and dirty
state. No timestamps, random IDs or absolute root paths enter a fixed-date report.
Same inputs, Git state, tool version and date yield identical bytes.
The evaluator is trusted; repo content cannot supply a plug-in to replace checks.

`python scripts/verify_project.py --out <new directory>` runs only this repository's
fixed reviewed acceptance commands, separately from the generic audit. It writes
logs, test/skip counts, normalized audit JSON and a checksum manifest, refuses to
overwrite existing evidence, and fails on any failed gate or skipped test.
Its code is trusted CI configuration, not an untrusted-manifest command runner.
Evidence is tied to tracked and nonignored source digests and Git state; checksums are integrity
checks, not signatures or independent approval. CI uploads the evidence even on
failure. Do not claim hosted validation until that revision actually runs there.

## Work Receipts (Milestone C)

The local candidate now implements versioned receipts and bounded integrity
verification. See [WORK_RECEIPTS.md](WORK_RECEIPTS.md) for the single authoritative
contract. Project audit still does not execute tests or authenticate receipt
producers. Full certification and semantic/human review remain UNKNOWN.
