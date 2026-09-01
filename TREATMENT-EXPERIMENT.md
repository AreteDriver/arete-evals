# Treatment experiment contract

**Status:** Contract represented in v1 manifests; live treatment experiment
deferred until the canonical public-project run is complete.

## Invariant

```text
scenario × model × treatment → outcome
```

The scenario, model, judge configuration, and scoring metrics remain fixed
while exactly one treatment changes. Treatments are versioned variant knobs
consumed by the target adapter; `arete-evals` does not add treatment execution
logic to the engine.

## Treatment contract

Every variant records:

| Field | Requirement |
|---|---|
| `id` | Stable human-readable identifier |
| `version` | Immutable behavior version |
| `kind` | `baseline`, `skill`, `mcp`, `instructions`, `subagent`, or `runtime` |
| `config` | Canonical serializable configuration; credential names only |
| `fingerprint` | SHA-256 of canonical treatment metadata, computed in the run manifest |

The target adapter is responsible for idempotent setup and best-effort cleanup
when a treatment changes external state. Setup and teardown outcomes must be
returned as output metadata before treatment runs become canonical evidence.

## Planned first experiment

| Arm | Treatment |
|---|---|
| A | Bare agent |
| B | Same agent plus one versioned, lazily loaded skill |
| C | Same agent, same skill, plus one versioned MCP capability |

Before execution:

1. Select and freeze a representative coding-case holdout.
2. Pin model, reasoning effort, instructions, tool versions, timeout, retry
   policy, and maximum spend.
3. Pre-register the primary correctness metric, minimum meaningful effect,
   and acceptable cost, latency, safety, and policy-denial regressions.
4. Choose repeated sample count based on an initial variance estimate.
5. Randomize arm order per case and prohibit mid-run tuning.

Primary outcome is task correctness using deterministic checks. Secondary
outcomes are input/output tokens, estimated cost, latency, tool errors, policy
denials, and human preference where applicable.

## Keep/reject rule

A treatment is retained only when its result is reproducible from stored
metadata and its correctness improvement clears the pre-registered practical
threshold without an unacceptable secondary regression. An interval spanning
zero is inconclusive.

## Implementation gate

Do not begin this experiment until:

- the v1 structured-response suite has one canonical live public-project
  bundle;
- live adapter metadata records setup and teardown status;
- the holdout and review protocol are frozen;
- the cost ceiling is approved.
