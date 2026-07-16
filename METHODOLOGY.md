# METHODOLOGY

**Version:** 0.1  
**Date:** 2026-07-05  
**Scope:** How `arete-evals` designs, runs, and calibrates LLM evaluation suites.

---

## 1. Eval Engineering vs Eval Practice

A harness with passing self-tests has caught nothing. This distinction is the foundation of the methodology.

- **Eval engineering** = building the framework: metric classes, scoring math, CLI, structural gates. This is the easy part.
- **Eval practice** = running it against messy production output and acting on the verdict. This is where false confidence lives.

The gap between them is API-boundary hygiene (dead keys, missing transitive deps, stale environment configs) and interpretive discipline (knowing when the eval is wrong, not just when the product is wrong).

**Rule:** Every suite must have at least one live run record in `results/` before it is considered proven. Self-tests green is necessary, not sufficient.

---

## 2. Suite Design Principles

### 2.1 Domain-neutral lead suites
The public face of a suite must be domain-neutral. `benchgoblins-ask` tests JSON-leak integrity, not fantasy sports. The sport is the fixture; the eval tests a generic failure mode (raw data shape leaking into a structured response field).

### 2.2 Structural gates first, rubric second, judge last
Three layers of defense, ordered by objectivity:

1. **Structural gates** — regex, schema, presence/absence. Zero LLM involvement. Fast, cheap, deterministic. `fail_fast` gates force FAIL regardless of composite score.
2. **Rubric metrics** — scored against a rubric (e.g., `personal-quality`, `code-edit`). Uses an LLM judge but with constrained scoring dimensions.
3. **Judge metrics** — open-ended LLM evaluation with full reasoning. Most expensive, most subjective, used only when the first two layers are insufficient.

### 2.3 `fail_fast` discipline
Any structural gate that detects a known-bad shape must force immediate failure. Do not let composite scoring dilute a clear structural violation.

---

## 3. Metric Taxonomy

The engine supports three metric classes, each with different cost/reliability tradeoffs:

| Class | Example | Cost | Subjectivity | Use When |
|-------|---------|------|--------------|----------|
| Structural | `regex_absence`, schema validation | Low | None | Known-bad shapes, contract violations |
| Rubric | `personal-quality` (6 dims) | Medium | Low-Medium | Scored comparison across runs |
| Judge | Open-ended reasoning evaluation | High | Medium-High | Novel failure modes, exploratory |

### 3.1 Failure Taxonomies
Every run is tagged with two orthogonal classifiers:

**Technical failure modes** (`failure_taxonomy.py`):
- `schema_drift` — output structure changed
- `hallucination` — factually incorrect content
- `wrong_answer` — correct format, incorrect substance
- `refused` — model declined to answer
- `over_budget` — cost exceeded threshold
- `timeout` — latency violation
- `contract_violation` — API promise broken
- `judge_disagreement` — two judges returned different verdicts
- `flaky` — non-deterministic failure
- `provider_error` — upstream API failure

**Content failure modes** (`failure_taxonomy_content.py`):
- `F1_missing_constraint` — requirement ignored
- `F2_wrong_assumption` — invalid premise baked in
- `F3_weak_evidence` — unsupported claim
- `F4_too_generic` — boilerplate, no specific insight
- `F5_overlong` — exceeded output budget
- `F6_poor_structure` — hard to parse or act on
- `F7_false_precision` — confidence not justified
- `F8_insufficient_adversarial_review` — obvious objections missed

A single output can carry one technical mode and multiple content modes.

---

## 4. Bootstrap A/B Comparison

### 4.1 When to use
Compare two eval runs (e.g., before/after a code change, or model A vs model B) when:
- Both runs use the **same suite** and **same metric set**
- The difference is the **system under test**, not the eval itself

### 4.2 Procedure
1. Run suite against baseline → `results/baseline-{hash}.json`
2. Run suite against candidate → `results/candidate-{hash}.json`
3. Compute per-case score deltas
4. Bootstrap 10,000 resamples with replacement from the delta distribution
5. Report 95% CI on the mean delta
6. Verdict:
   - CI entirely above 0 → candidate is better (statistically significant)
   - CI entirely below 0 → candidate is worse
   - CI spans 0 → inconclusive; need more cases or a sharper metric

### 4.3 Interpreting inconclusive results
An inconclusive result is not a null result. It means the signal is smaller than the noise floor of the current suite. Options:
- Add more cases (increase n)
- Sharpen the metric (reduce variance)
- Accept that the change has no practical effect

---

## 5. Run Record Philosophy

Every run produces a machine-readable record in `results/` containing:
- Full model output (for reproducibility)
- Per-case metric scores
- Aggregate statistics
- Timestamp, suite version, model identifier

**Why keep full outputs:** Evals are wrong too. The only way to diagnose "the eval failed" vs "the product failed" is to re-read the raw output.

**Retention policy:** Indefinite. Storage is cheap; regret is expensive. Records are named `{suite}-{hash}.json` where `hash` is a truncated SHA of the suite file + model identifier.

---

## 6. Calibration Process

### 6.1 Weekly cadence
Every Tuesday (or the first working day after):
1. Run the full battery against current production output
2. Spot-check 5% of cases manually
3. Flag cases where human judgment disagrees with eval verdict
4. If disagreement rate > 10%, freeze the suite for repair
5. Log calibration results in `results/calibration-YYYY-MM-DD.json`

### 6.2 Suite repair protocol
When a suite is frozen:
1. Diagnose: is the suite too strict, or did the product regress?
2. If suite is too strict: relax gates, add tolerance, or split into versioned suites
3. If product regressed: file a `setup-blocker` issue, do not relax the gate
4. Re-run calibration until human agreement returns to > 90%

### 6.3 Rubric drift
Rubrics degrade over time as model capabilities shift. A rubric calibrated on Claude 3.5 may under-score Claude 4.6 on dimensions that are now table stakes. Review rubrics quarterly.

---

## 7. Case Study: benchgoblins-ask

**Purpose:** Guard against JSON-leak regression in a structured LLM output pipeline.

**Setup:**
- 20 cases covering waiver, trade, and start/sit scenarios
- Six `fail_fast` structural gates using `regex_absence`
- Gate pattern: detect raw JSON shape (`"recommendations"`, `"drop_candidates"`) inside the `rationale` field

**Live run result:** 15/20 passed. 5 failures, all `waiver_*` cases, all tripping `regex_absence` at 0%.

**First read:** The eval caught a live regression. Half the waiver path still leaking.

**Actual diagnosis:** The gate was too brittle. Model output contained the word "recommendations" in natural language ("I need more context to give you specific waiver recommendations..."), not as JSON keys. The gate fired on substring match, not structural match.

**Lesson:** A structural gate that matches natural language is a false positive factory. The fix: anchor the regex to JSON shape (`"rationale": "..."recommendations` with key-value context), not bareword presence.

**Why this matters:** Without the live run, the suite would have sat at "391 passing tests, zero catches" — falsely reassuring. The eval was wrong. The practice caught it.

---

## 8. Known Limitations

1. **Judge subjectivity:** Rubric metrics depend on LLM judge temperature and prompt version. Results are reproducible only with pinned judge configurations.
2. **Structural gate brittleness:** Regex gates fail when output format changes innocently. Version suites alongside product versions.
3. **Bootstrap assumptions:** The 95% CI assumes independent cases. Correlated cases (e.g., all hitting the same API endpoint) inflate confidence.
4. **Calibration cost:** Weekly manual spot-checking is expensive. The harvester mechanism (v0.1+) aims to auto-generate candidate cases from transcripts, but human sign-off remains required.

---

## 9. References

- **Suites:** `suites/` directory
- **Run records:** `results/` directory
- **Triage UI:** Open `tools/triage.html` in a browser, import any `results/*.json`
- **Engine:** `pip install -e ../evalcore` (see `requirements.txt`)
- **Case study full record:** `results/benchgoblins-ask-6ea664d3.json`

---

## 10. Changelog

| Date | Change |
|------|--------|
| 2026-07-05 | v0.1 — Initial methodology document. Covers engineering vs practice distinction, metric taxonomy, bootstrap A/B, calibration protocol, and benchgoblins-ask case study. |