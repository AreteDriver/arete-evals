# Security authority

Owner: AreteDriver. Reviewed: 2026-09-29. Dependency review every 6–8 weeks and
before release. Report a suspected secret privately to the owner, never in a
public report. No credentials are required for offline checks.

## Read-only project audit

Treat manifests, instructions, evidence references and commands as untrusted data.
The auditor never executes their contents, imports project modules or fetches URLs.
Fixed Git probes have a timeout, disable fsmonitor and optional locks, and do not
run hooks or contact remotes. Git configuration/executable and the installed
auditor environment remain trusted dependencies. Do not run against a concurrently
mutating filesystem; path checks are not a kernel sandbox.

Inputs are limited to 1 MiB each, 16 MiB total, 256 files, 20 YAML levels and schema-bounded collections.
Symlinks, traversal, absolute/drive paths, aliases, duplicate keys and non-regular
files are rejected. A project root explicitly supplied by the caller is resolved;
referenced paths cannot leave it. No raw document bodies or manifest values are
included in schema errors. Reports contain identity, relative evidence paths and
hashes; review these metadata before publishing. A hash proves bytes, not origin.

Tracked sensitive filenames fail the gate without reading their contents.
The `.env` exclusion is checked. This is not a secret scanner or comprehensive
security certification; content review remains mandatory. Never include real
secrets in manifests, receipts, fixtures, reports, logs or commits.

## Existing trusted execution paths

Suite runners, live adapters and public bundle exports predate the project audit.
They are for trusted local suites/bundles only. Known limits: selected schema
checks instead of full runtime schema enforcement; artifact path assumptions;
synchronous HTTP I/O with unbounded response size. These require bounded
hardening before accepting hostile bundle input or widening live execution.
No claim of production security or hostile-input safety applies to these paths.

Private outputs stay ignored under runs/private. Hashes-only publication still
requires actual human review; a reviewer string is not authenticated approval.
Run-directory non-overwrite and checksums do not prevent deliberate filesystem
editing. Preserve original evidence and create new versions for corrections.
