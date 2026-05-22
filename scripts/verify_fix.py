"""Reproduce the metric-fix verification from the benchgoblins-ask case study.

Applies the suite's current `regex_absence` patterns to the 20 stored
responses from run 6ea664d3 and reports per case. With the fixed
(JSON-key-anchored) patterns this prints 0/20 false positives; with the
original bare-word patterns it printed 5/20 — same inputs, only the metric
changed, which isolates the fix.

Requires: pyyaml.  Usage:  python scripts/verify_fix.py
"""
import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
suite = yaml.safe_load((ROOT / "suites" / "benchgoblins-ask.yaml").read_text())
data = json.loads((ROOT / "results" / "benchgoblins-ask-6ea664d3.json").read_text())

abs_patterns = [m["pattern"] for m in suite["metrics"] if m["type"] == "regex_absence"]

print("regex_absence patterns under test:")
for p in abs_patterns:
    print(f"  {p}")
print()

fails = 0
for r in data["results"]:
    leaks = [p for p in abs_patterns if re.search(p, r["output"])]
    if leaks:
        fails += 1
    print(f"  {r['case_name']:26} absence-gates={'LEAK-DETECTED' if leaks else 'clean'}")

print()
print(f"absence-gate false-positive count: {fails}/20")
print("RESULT:", "all clean — fix holds" if fails == 0 else f"{fails} flagged — inspect")
