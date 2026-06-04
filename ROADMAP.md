# arete-evals — Consolidation Roadmap

**Status:** planning locked 2026-06-04. No build started. Phase 1 is firm; Phases 2–3 are provisional and get re-planned from real signal at the 50% checkpoint.

## Premise

The eval *harness* already exists (animus-forge `evaluation/`, ~4,205 LOC, 13 pluggable metrics, A/B with bootstrap CI, two failure taxonomies). The eval *practice* lives here (suites + run records + the "391 passing tests had caught nothing" case study). The problem is not that the tool is unbuilt — it is that the same instinct got built ~11 times across scattered repos (anchormd, agent-lint, context-hygiene, prompt-debt, drift-monitor, autopsy, signal, calibrate, verdict, forge-evals, arete-evals) and never consolidated. This is a **finish problem, not a build problem.** The roadmap consolidates the scattered parts into one composable socket + plugins, with arete-evals as the practice home.

## Decisions (locked this session)

- **Credibility artifact, not a business, this quarter.** No Stripe / license / seat layer. anchormd is the cautionary case: commercial scaffolding ahead of demand, zero customers.
- **Consolidate, don't construct.** No new product, no rename churn, no repo #12.
- **Engine = its own module (the socket).** Extracted from forge `evaluation/`, decoupled, installable. Consumed by arete-evals (practice + narrative) and — later, as a separate step — animus-forge replacing its internal copy.
- **arete-evals = home** for suites, run records, and the narrative. The engine is a dependency.
- **benchgoblins-ask = technical proof + deep case study, not the public face.** Public face = a domain-neutral lead suite. (The sport is just the fixture; the eval tests LLM-output JSON-leak integrity.)
- **Surfaces are harvested from existing fleet work**; one harvester mechanism makes them self-replenishing. No new surface-generator repos.

## Falsifiable v0.1 target

> `pip install` the extracted engine → run a domain-neutral suite + `benchgoblins-ask` against real model output → get a scored report with bootstrap CI. The arete-evals case study reproduces on an **installable tool**, not animus-internal code.

If that sentence is not true, v0.1 is not done. Everything else is v0.2+.

## Source map

| Disposition | Repo / module | Action |
|---|---|---|
| **Extract (socket)** | forge `evaluation/` (10 of 13 modules have zero animus coupling) | lift; decouple 3 seams (`store`, `metrics`, `base`) |
| **Cannibalize → plugin** | drift-monitor `spc.py` | SPC drift/regression metric (the live-quality tier) |
| **Cannibalize → plugin** | signal `analyzers/quality.py` | EpistemicQuality metric (regex bank) |
| **Cannibalize → plugin** | context-hygiene `analyzers/deep.py` | deep LLM-analyzer tier (heuristic↔LLM dual path) |
| **Cannibalize → idea** | autopsy `analyzers.py` | fold failure taxonomy into `FailureClassifier` enums |
| **Dispose (stub)** | calibrate, verdict, prompt-debt | delete after sign-off; salvage concepts only |
| **Decide-disposition** | drift-monitor, context-hygiene, anchormd | shipped/used — salvage code, then per-repo keep/deprecate/retire |
| **Keep-standalone** | agent-lint (`agentlinter`, shipped) | do not merge — different domain (static YAML lint) |

## Phases & session map

Each session = one sitting, one definition-of-done (DoD). MASTER + AI_WORKFLOW_BUILD templates govern each session; this roadmap governs the arc.

### Phase 1 — Extract & decouple (v0.1 spine) — FIRM
- **S0 (gate):** namespace synonym-grep (≥5 terms) + name the engine package. *DoD: name chosen, no collision, dir/repo scaffolded.*
- **S1:** move the 10 zero-coupling modules + their tests. *DoD: they import and pass standalone.*
- **S2:** decouple `store.py` (storage seam → pluggable backend). *DoD: engine persists with no animus import.*
- **S3:** decouple `metrics.py` / `base.py` (LLM-client seam → injected client). *DoD: judge metrics run with an injected client; zero animus imports remain.*
- **S4:** port the CLI (`run` / `compare` / `rubrics` / `results`). *DoD: `eval run` works on a sample suite.*
- **S5:** domain-neutral lead suite (`personal-quality` rubric + one structural gate). *DoD: neutral suite runs green; becomes README example #1.*
- **S6:** arete-evals consumes the package; `benchgoblins-ask` runs on it. *DoD: case study reproduces on the installed engine; loop closed = v0.1 target sentence true.*
- **CHECKPOINT 50%:** v0.1 target true. Review: keep/cut, scope drift, is the neutral suite the right face? Re-plan Phases 2–3 from here.

### Phase 2 — Cannibalize as plugins + Surfaces — PROVISIONAL
Cannibalize:
- **S7:** drift-monitor `spc.py` → DriftMetric. *DoD: a regression is caught across two runs via SPC.*
- **S8:** signal `quality.py` → EpistemicQuality metric. *DoD: plugs in, scores a sample.*
- **S9:** context-hygiene `deep.py` → deep LLM-analyzer tier. *DoD: heuristic+LLM dual path available.*
- **S10:** autopsy taxonomy → `FailureClassifier`. *DoD: new failure modes tag results.*

Surfaces (each reuses an existing rubric; one session each):
- **S11:** forge code-edit suite (`code-edit` rubric).
- **S12:** Gatekeeper `ai_analyzer` suite (`briefing-quality` rubric).
- **S13:** Dossier NER suite (structural metrics — no judge).
- *Verify-then-add:* animus `brief`, Ogma `synthesize`, TIAID content (maps to content failure taxonomy F1–F8).
- **CHECKPOINT 75%:** dogfood the **full battery** against real output + **modularity proof** — add one new metric plugin in under a session, recorded.

### Phase 3 — Harvester, finish, present — PROVISIONAL
- **S14:** harvester v0 — golden-case capture (`GoldenCase` primitive exists). *DoD: one command snapshots a live output as a case.*
- **S15:** harvester v1 — transcript→case generator (animus transcripts). *DoD: a session transcript yields candidate cases.*
- **S16:** approved disposals (stubs first; shipped repos only on explicit per-repo sign-off). *DoD: namespace reduced; pointers left.*
- **S17:** README/narrative — arete-evals story as the tool's story. *DoD: a stranger understands what it is and sees the "eval was wrong" lesson.*
- **S18:** Ted review (exit trigger for "private until proven"). *DoD: Ted has run it and given feedback.*
- **CHECKPOINT 100%:** installable, multi-surface dogfooded, plugin-extensible, harvester live, reviewed.

## Disposal discipline

Nothing deleted without per-repo sign-off. Shipped/used repos (drift-monitor, context-hygiene, agent-lint, anchormd) get a disposition decision, never a default delete. Salvage code first, then decide keep / deprecate-with-pointer / retire.

## Open gates

- **Engine package name** — gated on the S0 synonym-grep (namespace rule; broke 3× before, do not skip).
- **Engine home** — assumed: its own module consumed by arete-evals + forge. Reversible at S0.
- **Per-repo disposals** — sign-off at S16.

## Out of scope (v0.1–v1)

Monetization / license / Stripe layer; agent-lint merge; public community + marketing; the forge internal-copy migration (a separate later step — do not entangle timelines).

## Provenance

Planned 2026-06-04. Sources: projects-folder + GitHub sweep, forge `evaluation/` deep-read, cannibalize-target subagent inventory. Operating loop: concrete target → honest gap → one-session parts → checkpoint review.
