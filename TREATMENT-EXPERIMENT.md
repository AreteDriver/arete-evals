# Treatment experiment contract

**Status:** Sprint 0 design ready; engine implementation blocked on access to the
canonical `evalcore` source.

## Decision

Treatments are reproducible changes to an agent's operating environment, not
new scenarios and not free-form run labels. The invariant experiment shape is:

```text
scenario × model × treatment → outcome
```

The scenario, model configuration, judge configuration, and scoring metrics
remain fixed while exactly one treatment changes. Treatment support belongs in
`evalcore`; `arete-evals` remains the home for suites and run records. Do not
build a second execution harness here.

## Minimum engine contract

A treatment definition must record:

| Field | Requirement |
|---|---|
| `id` | Stable, human-readable identifier |
| `version` | Immutable version for the treatment behavior |
| `kind` | `baseline`, `skill`, `mcp`, `instructions`, `subagent`, or `runtime` |
| `config` | Canonical, serializable configuration with secrets represented only by environment-variable names |
| `setup` | Idempotent environment preparation |
| `teardown` | Best-effort cleanup that runs after pass, failure, or timeout |
| `fingerprint` | SHA-256 of canonical treatment metadata and referenced artifact versions |

Every run record must add the treatment ID, version, fingerprint, setup status,
and any setup/teardown failure. Existing full model output, per-case metrics,
suite version, model ID, cost, tokens, and latency remain mandatory.

## First experiment

Test whether one existing skill and one MCP capability materially improve a
fixed coding workload:

| Arm | Treatment |
|---|---|
| A | Bare agent |
| B | Same agent plus one lazily loaded skill |
| C | Same agent, same skill, plus one MCP capability |

Use at least 10 representative cases. Run all three arms for each case, with
arm order randomized per case. Pin the model, reasoning effort, system
instructions, tool versions, timeout, and maximum spend before the first run.
Do not tune an arm after observing partial results.

Primary outcome: task correctness using deterministic checks where possible.
Secondary outcomes: input/output tokens, estimated cost, wall-clock latency,
tool failures, and policy denials. Report paired per-case deltas and a bootstrap
95% confidence interval. Keep raw outputs even when the eval verdict is later
found to be wrong.

## Keep/reject rule

Keep treatment support only if the experiment can be reproduced from stored
metadata and distinguishes the environmental change from model or scenario
changes. Keep an individual treatment when it improves correctness without an
unacceptable cost, latency, or safety regression. An interval spanning zero is
inconclusive, not evidence of improvement.

## Implementation gate

The local checkout contains `arete-evals`, which explicitly declares
`evalcore>=0.1.0`, but no sibling `evalcore` source is available and no
authoritative public repository was discoverable during Sprint 0. Required
next action: restore or identify the canonical engine repository, then add the
treatment model, serialization, CLI selection, setup/teardown lifecycle, and
engine-level tests there before creating live run records here.
