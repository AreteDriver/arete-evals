"""Reproduce the benchgoblins-ask case study on the evalcore engine.

Loads the suite through evalcore's ``SuiteLoader`` — which instantiates the
engine's metric plugins — and replays the 20 stored model outputs from run
6ea664d3 through the engine's ``RegexAbsenceMetric`` gates. With the fixed
JSON-key-anchored patterns this reports 0/20 false positives: the same verdict
the case study reached, now produced by the installable engine rather than
animus-forge-internal code.

    pip install -e ../evalcore
    python scripts/reproduce_on_evalcore.py
"""

import json
from pathlib import Path

from evalcore.base import EvalCase
from evalcore.loader import SuiteLoader

ROOT = Path(__file__).resolve().parent.parent
suite = SuiteLoader(ROOT / "suites").load_suite("benchgoblins-ask")
data = json.loads((ROOT / "results" / "benchgoblins-ask-6ea664d3.json").read_text())

absence_gates = [m for m in suite.metrics if type(m).__name__ == "RegexAbsenceMetric"]
print(f"engine: evalcore | suite: {suite.name} | regex_absence gates: {len(absence_gates)}")
print()

false_positives = 0
for r in data["results"]:
    case = EvalCase(input="", name=r["case_name"])
    leaked = any(gate.score(r["output"], None, case) < 1.0 for gate in absence_gates)
    print(f"  {r['case_name']:28} {'LEAK-DETECTED' if leaked else 'clean'}")
    if leaked:
        false_positives += 1

print()
print(f"regex_absence false positives: {false_positives}/{len(data['results'])}")
assert false_positives == 0, "a gate false-fired on stored output — the fix regressed"
print("OK — benchgoblins-ask case study reproduces on the installed evalcore engine")
