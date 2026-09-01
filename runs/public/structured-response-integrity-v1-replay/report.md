### arete-evals/structured-response-integrity - `baseline`

- model: `recorded-fixture`  mode: `replay`  dataset: `v1`  cases: 10x1

| metric | value |
| --- | ---: |
| schema_valid | 1.0000 |
| decision_valid | 0.8000 |
| rationale_valid | 1.0000 |
| no_serialized_json_leak | 0.7000 |
| details_valid | 0.8000 |
| contract_pass | 0.3000 |

### arete-evals/structured-response-integrity - `candidate`

- model: `recorded-fixture`  mode: `replay`  dataset: `v1`  cases: 10x1

| metric | value |
| --- | ---: |
| schema_valid | 1.0000 |
| decision_valid | 1.0000 |
| rationale_valid | 1.0000 |
| no_serialized_json_leak | 1.0000 |
| details_valid | 1.0000 |
| contract_pass | 1.0000 |

## **PASS** - arete-evals/structured-response-integrity

`candidate` vs `baseline` - contract_pass improved

| metric | baseline | candidate | delta |
| --- | ---: | ---: | ---: |
| contract_pass **(improved)** | 0.3000 | 1.0000 | +0.7000 |
| decision_valid | 0.8000 | 1.0000 | +0.2000 |
| details_valid | 0.8000 | 1.0000 | +0.2000 |
| no_serialized_json_leak | 0.7000 | 1.0000 | +0.3000 |
| rationale_valid | 1.0000 | 1.0000 | +0.0000 |
| schema_valid | 1.0000 | 1.0000 | +0.0000 |

**Guardrails**

- [ok] `contract_pass` - 1.0000 ok
- [ok] `no_serialized_json_leak` - 1.0000 ok
