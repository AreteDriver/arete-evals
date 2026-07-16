# Project Status

| Attribute | Value |
|-----------|-------|
| Status | **PARTIAL** |
| Last verified | 2026-07-16 |
| Installable? | Partial — engine is installable, suites are research artifacts |
| Tested? | Engine self-tests pass; live-run records verified (see `results/`) |
| Documented? | README + case studies; no hosted docs yet |

## What Works

- **Eval Engine (`evalcore`):** Structural metrics, rubric scoring, A/B compare with bootstrap CI, two failure taxonomies (technical + content)
- **Live Run Records:** `benchgoblins-ask` suite run against production — 15/20 passed, 5 failed, all failures analyzed and explained
- **Triage UI:** Browser-based tool for inspecting run records (`tools/triage.html`)
- **Integration:** Designed as measurement layer for Animus Forge — every completed Forge task spawns an eval run

## What Doesn't Work Yet

- No PyPI package for `evalcore` (install from sibling directory)
- No automated CI for suite execution against live products
- No hosted dashboard for eval trends
- `config_loader` and `rate_limiter` test cases need fixing before autonomous weekly calibrations

## Install

```bash
# Engine
cd evalcore  # sibling to this repo
pip install -e .

# This repo (suites + records)
pip install -r requirements.txt
```

## Relationship to Animus

This repository is the **eval practice** companion to Animus. The harness lives in `evalcore`; this repo holds the suites, run records, and case studies that prove the harness catches real regressions.
