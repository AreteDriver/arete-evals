# Epistemic Quality Patterns

**Source:** Extracted from `AreteDriver/signal-audit` (archived 2026-06-22)  
**Purpose:** Heuristic regex-based scoring for AI output quality — hedging, overconfidence, contradictions, filler, citations, reasoning markers, structure.  
**Target:** Port into arete-evals engine as an `EpistemicQuality` metric plugin (per ROADMAP Phase 2: cannibalize `signal analyzers/quality.py`).

---

## 1. Regex Pattern Bank

All patterns are case-insensitive (`re.IGNORECASE`).

### Hedging Patterns
```regex
\b(maybe|perhaps|possibly|might|could be|I think|it seems|I'm not sure|arguably|it depends)\b
```
**Use:** Detects uncertainty markers that may indicate weak evidence or low confidence.

### Overconfidence Patterns
```regex
\b(definitely|certainly|always|never|impossible|guaranteed)\b
```
**Use:** Detects absolute claims that are statistically unlikely to be justified.

### Contradiction Markers
```regex
\b(however|but|on the other hand|actually|in contrast|contrary to|despite|although)\b
```
**Use:** Detects internal contradictions or hedged reversals. Also doubles as reasoning-complexity signal when paired with reasoning markers.

### Filler Words
```regex
\b(basically|essentially|actually|literally|really|very|just|simply|obviously|clearly)\b
```
**Use:** Detects hedging/filler language that reduces signal density. "Obviously" and "clearly" are epistemic red flags — they assert obviousness without evidence.

### Citation Detection
```regex
(https?://|according to|source:|reference:|\[\d+\])
```
**Use:** Detects whether the output grounds claims in external references. Positive signal for accuracy dimension.

### Code Block Detection
```regex
```[\s\S]*?```
```
**Use:** Structural signal — presence of code blocks indicates completeness in technical outputs.

### Reasoning Markers
```regex
\b(because|therefore|since|given that|as a result|this means|consequently|thus)\b
```
**Use:** Detects causal/explanatory structure. Absence in long text = assertions without reasoning.

### Structure Markers (Markdown)
```regex
(^#{1,4}\s|\n#{1,4}\s|^\d+\.\s|\n\d+\.\s|^[-*]\s|\n[-*]\s)
```
**Use:** Detects structured formatting (headers, numbered lists, bullet lists). Positive signal for clarity and completeness.

---

## 2. Scoring Dimensions

Six dimensions, each scored 0.0–10.0. Baseline scores and flag names:

| Dimension | Baseline | Key Inputs | Flags |
|-----------|----------|------------|-------|
| **Accuracy** | 7.0 | hedge ratio, overconfidence count, citation count | `excessive_hedging`, `overconfident_claims` |
| **Reasoning** | 6.0 | reasoning markers, contradiction markers | `no_reasoning_markers`, `internal_contradictions`, `assertions_without_reasoning` |
| **Completeness** | 7.0 | word count, code blocks, structure, truncation | `too_brief`, `appears_truncated` |
| **Clarity** | 7.0 | filler ratio, avg sentence length, structure | `excessive_filler`, `long_sentences` |
| **Relevance** | 7.0 | query word overlap | `low_query_relevance` |
| **Consistency** | 8.0 | contradiction markers | `many_contradicting_signals` |

### Accuracy Scoring Logic
```
hedge_ratio = hedges / words
if hedge_ratio > 0.02:   score -= 1.5, flag "excessive_hedging"
elif hedge_ratio > 0.01: score -= 0.5

if overconf > 3:  score -= 2.0, flag "overconfident_claims"
elif overconf > 0: score -= 0.5

if citations > 0: score += min(1.5, citations * 0.5)

clamp(score, 0.0, 10.0)
```

### Reasoning Scoring Logic
```
if markers > 5:  score += 2.0
elif markers > 2: score += 1.0
elif markers == 0: score -= 2.0, flag "no_reasoning_markers"

if contradictions > 3: score -= 1.5, flag "internal_contradictions"
elif contradictions > 0 and markers > 0: score += 0.5  # nuanced

if words > 50 and markers == 0: flag "assertions_without_reasoning"

clamp(score, 0.0, 10.0)
```

### Completeness Scoring Logic
```
if words < 20: score -= 3.0, flag "too_brief"
elif words < 50: score -= 1.0

if has_code: score += 1.0
if has_structure: score += 1.0

if text.strip().endswith("...") or text.strip().endswith("etc"):
    score -= 1.0, flag "appears_truncated"

clamp(score, 0.0, 10.0)
```

### Clarity Scoring Logic
```
filler_ratio = fillers / words
if filler_ratio > 0.03: score -= 2.0, flag "excessive_filler"
elif filler_ratio > 0.015: score -= 1.0

avg_sentence_len = words / sentences
if avg_sentence_len > 35: score -= 1.5, flag "long_sentences"
elif avg_sentence_len > 25: score -= 0.5

if has_structure: score += 1.0

clamp(score, 0.0, 10.0)
```

---

## 3. Grade Thresholds

Overall score = mean of dimension scores, scaled to 0–100.

| Grade | Overall Score | Meaning |
|-------|---------------|---------|
| **A** | ≥ 80 | Strong across dimensions |
| **B** | ≥ 65 | Good, minor gaps |
| **C** | ≥ 50 | Acceptable, notable weaknesses |
| **D** | ≥ 35 | Poor, significant problems |
| **F** | < 35 | Fails basic quality bar |

---

## 4. Known Limitations

1. **Language bias:** Regex patterns are English-centric. Non-English output will under-score on hedging/filler dimensions.
2. **Domain sensitivity:** Technical outputs (code, math) score differently from prose. The completeness bonus for code blocks skews scores toward technical content.
3. **Contradiction false positives:** "However" and "but" are also standard transition words. The contradiction flag fires on any occurrence, not actual logical contradiction.
4. **Query dependence:** The relevance dimension requires a query string. Without it, the dimension is neutral (baseline 7.0).
5. **Ratio thresholds are arbitrary:** The 0.02 hedge_ratio threshold, 0.03 filler_ratio threshold, and 35-word sentence threshold were tuned on a small sample. They need calibration against a labeled corpus.

---

## 5. Port Notes

When implementing as an `EpistemicQuality` metric plugin in the arete-evals engine:

- **Parameterize thresholds:** Make hedge_ratio, filler_ratio, and sentence-length thresholds configurable per-suite.
- **Add corpus calibration:** Run the metric against a labeled quality dataset to learn optimal thresholds.
- **Consider language packs:** The pattern bank should be extensible per-language.
- **Separate structural from semantic:** Code-block and structure detection are structural metrics that should optionally feed into a structural gate, not just the epistemic score.
- **Flag deduplication:** The same text pattern (e.g., "however") can trigger both reasoning and contradiction logic. Ensure flags are deduplicated in the output.

---

## 6. Provenance

Extracted 2026-07-05 from `AreteDriver/signal-audit` (commit history: 2026-01 through 2026-06, 40 files, 10+ test files). Original author: AreteDriver. Original license: MIT.