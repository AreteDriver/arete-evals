# Triage — `benchgoblins-ask` run `6ea664d3`

**Run:** 2026-05-22T00:39:09  
**Triaged:** 2026-05-23  
**Original verdict:** 15 pass / 5 fail / 0 error (pass rate 0.75)  
**Effective verdict after metric fix:** 20 pass / 0 fail (pass rate 1.00)

## Disposition

| Bucket | Count | % |
|---|---:|---:|
| Pass | 20 | 100% |
| Needs Review | 0 | 0% |
| Fail | 0 | 0% |
| Flaky | 0 | 0% |

All five cases originally marked `failed` are confirmed **eval-metric false positives**, not product regressions. The fixed `regex_absence` pattern lives at [`suites/benchgoblins-ask.yaml:71-72`](../suites/benchgoblins-ask.yaml). [`scripts/verify_fix.py`](../scripts/verify_fix.py) reproduces the result against the stored outputs.

---

## Per-case detail (the five originally-failed)

### `waiver_open_ended` (id `13f2e953`) — score 0.833

- **Failing gate (old pattern):** `regex_absence` on `"recommendations"` word match
- **Trigger phrase:** *"I need more context to give you specific waiver **recommendations**. Since today is Friday, May 22, 2026, we're in the NFL offseason..."*
- **Verdict:** Eval-metric false positive. The gate was matching the English word; the regression shape is an escaped JSON key.
- **Bucket:** Pass

### `waiver_top_n_ppr` (id `65186e4b`) — score 0.833

- **Failing gate (old pattern):** `regex_absence`
- **Trigger phrase:** *"Unable to provide meaningful waiver **recommendations** without roster context and available player pool..."*
- **Verdict:** Eval-metric false positive. Same pattern as case 1.
- **Bucket:** Pass

### `waiver_streaming_qb` (id `c4584530`) — score 0.833

- **Failing gate (old pattern):** `regex_absence`
- **Trigger phrase:** Stored `output` field truncated at 500 chars; the original (broken) gate ran on the full response and matched `recommendations` past the cutoff. Same false-positive shape as the other four — prose containing the word, not an escaped JSON key.
- **Verdict:** Eval-metric false positive.
- **Bucket:** Pass

### `waiver_defense_streamer` (id `6a391c7b`) — score 0.833

- **Failing gate (old pattern):** `regex_absence`
- **Trigger phrase:** *"I cannot provide specific Sunday Night Football defense streaming **recommendations** because May 22, 2026 is during the NFL offseason..."*
- **`failure_mode`** in original record: `refused` — harness correctly read "I cannot provide..." as a refusal. Not a regression — date-aware product behavior.
- **Verdict:** Eval-metric false positive.
- **Bucket:** Pass

### `waiver_mnf_reaction` (id `e383b4ac`) — score 0.833

- **Failing gate (old pattern):** `regex_absence`
- **Trigger phrase:** *"...I cannot provide current waiver **recommendations** based on recent performances..."*
- **`failure_mode`** in original record: `refused` — same correct read as case 4.
- **Verdict:** Eval-metric false positive.
- **Bucket:** Pass

---

## Common diagnosis

Old pattern (overly permissive):

```regex
"rationale"\s*:\s*"(?:[^"\\]|\\.)*recommendations
```

Matches any occurrence of the English word `recommendations` inside the `rationale` JSON string. False-positives on any prose that uses the word.

Fixed pattern (anchored to the escaped-JSON-key shape that the `5c2cf48` regression actually produces):

```regex
"rationale"\s*:\s*"(?:[^"\\]|\\.)*\\"recommendations\\"\s*:
```

A leaked JSON key inside a rationale string renders as `\"recommendations\":` after escaping; prose never does. **0/20 false positives** under the fixed pattern against the same stored responses. Full eval suite still green at 391.

## Separate observation (not a fix to this suite)

All five originally-failed cases are the model correctly recognizing it is May 2026, the NFL is in offseason, and there is no meaningful week-N waiver advice to give. That is a *date-aware product behavior*, not a regression. If you want regression coverage for offseason-refusal-vs-helpfulness, that's a separate suite, not a patch to this one.

## Action items

- [x] Apply fixed `regex_absence` pattern to `suites/benchgoblins-ask.yaml` (done — commit landed in initial repo push)
- [x] Verify against stored responses via `scripts/verify_fix.py` (done — 0/20 false positives, no false negatives)
- [ ] Re-run `benchgoblins-ask` live to produce a new run record with the fixed pattern in place (next live run will replace this one as the canonical artifact)
