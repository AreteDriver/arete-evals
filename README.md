# arete-evals

LLM evaluation suites — and the records of what running them found.

The evaluation **harness** lives in [`animus-forge`](https://github.com/AreteDriver/animus-docs): suites, structural and rubric metrics, A/B compare with bootstrap CI, and two failure taxonomies. This repository holds the **suites run against real products** and the **run records** — including the runs where the eval itself turned out to be wrong.

The premise: a harness with passing self-tests has caught nothing. Eval *engineering* is building the framework. Eval *practice* is running it against messy production output and acting on the verdict. This repo is the practice.

## Layout

```
suites/    eval suite definitions (YAML)
results/   run records — raw model output + per-case metric scores
scripts/   reproducible verification
```

## Case study: the first live run of `benchgoblins-ask`

I had an LLM eval harness with 391 passing tests. It had caught nothing.

That sentence is the whole point. A harness that tests *itself* — its metric classes, its scoring math, its CLI — is eval *engineering*. Running it against real, messy, production model output and acting on what it says is eval *practice*. They are not the same thing, and the gap between them is where false confidence lives.

### The setup

`animus-forge` has an evaluation framework: suites, metrics, rubrics, A/B compare with bootstrap CI, two failure taxonomies. Built, tested, green.

One suite — [`benchgoblins-ask`](suites/benchgoblins-ask.yaml) — guards a specific shipped fix. [BenchGoblins](https://benchgoblins.com) (a fantasy-sports decision product) had a regression where raw waiver-shape JSON (`{"recommendations": [...], "drop_candidates": [...]}`) leaked straight into the chat `rationale` field instead of being mapped into the response envelope. Commit `5c2cf48` fixed it. The suite is 20 cases and six `fail_fast` structural gates — regex checks that catch that leak shape without judge subjectivity. Any one gate failing forces the case to FAIL regardless of composite score.

All of that existed. None of it had ever run against the live product.

### The friction nobody writes about

Wiring the harness to production was three failures before a result:

1. The harness's API key was dead — a 401 that a stale note in my own memory had flagged 12 days earlier and I'd never acted on.
2. The adapter imports the product's code in-process; the harness venv was missing one of the product's transitive dependencies (`prometheus_client`).
3. Only then — using the product's *own* working key, which is the correct key to evaluate it with anyway — did 20 real calls go through.

This is "API-boundary hygiene," and it's the unglamorous majority of eval work. The metrics are the easy part.

### The result

15 of 20 passed. Five failed — and all five were the same shape: `waiver_*` cases, all tripping one gate, a `regex_absence` check, at 0%. ([Full run record.](results/benchgoblins-ask-6ea664d3.json))

My first read was the exciting one: *the eval caught a live regression.* Half the waiver path still leaking.

It hadn't.

### The diagnosis

I pulled the five failing responses. Every one was a model output like:

> "I need more context to give you specific waiver **recommendations**. Since today is May 2026, we're in the NFL offseason..."

The gate's pattern:

```
"rationale"\s*:\s*"(?:[^"\\]|\\.)*recommendations
```

It fails the case if the word `recommendations` appears anywhere in the rationale. It was built to catch a leaked JSON *key*. It was matching the plain English *word*. The five "failures" were the model writing an ordinary, correct sentence — offseason hedges that happened to use a word.

No regression. The `5c2cf48` fix is holding. The bug was in the eval metric.

### The fix

Anchor the pattern to the escaped-JSON-key shape — a leaked key inside a JSON string renders as `\"recommendations\":`, which prose never does:

```
"rationale"\s*:\s*"(?:[^"\\]|\\.)*\\"recommendations\\"\s*:
```

Verified the controlled way — applied the new pattern to the exact 20 stored responses from the original run. Same inputs, only the metric changed: **0/20 false positives, down from 5/20, no false negatives.** Full eval suite still green at 391. [`scripts/verify_fix.py`](scripts/verify_fix.py) reproduces it.

### The lesson

The first live run of an eval harness mostly finds bugs in the eval harness. That is not the harness failing — that is the harness finally earning the right to be trusted.

A metric you have never run against real production output is a hypothesis, not a guardrail. Mine was a reasonable hypothesis — "a leaked JSON key contains the word `recommendations`" — that was true and useless, because so does every sentence about recommendations. I would not have found that by adding more unit tests. The tests all passed. I found it because I ran the thing, against reality, and read the five things it told me were wrong.

Ship the eval. Then run it against production and be ready for the first verdict to be about *you*.

---

*Harness: `animus-forge`. Suite: `benchgoblins-ask` (20 cases). Run `6ea664d3`, 2026-05-22.*
