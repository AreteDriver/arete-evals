"""Recheck the historical pattern against the stored, truncated outputs.

Applies the suite's current `regex_absence` patterns to the 20 stored
responses from run 6ea664d3 and reports per case. With the fixed
(JSON-key-anchored) patterns this prints 0/20 hits. This historical artifact
can bound observed false positives on the retained prefixes; it cannot measure
false negatives because it contains no known-bad leaked-output controls.

Requires: pyyaml.  Usage:  python scripts/verify_fix.py
"""

import json
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
suite = yaml.safe_load(
    (ROOT / "case-studies" / "benchgoblins-ask" / "suite-v0.yaml").read_text()
)
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
    print(
        f"  {r['case_name']:26} absence-gates={'LEAK-DETECTED' if leaks else 'clean'}"
    )

print()
print(f"fixed-pattern hits in stored output prefixes: {fails}/20")
print(
    "RESULT:",
    "no hits in retained prefixes" if fails == 0 else f"{fails} flagged — inspect",
)
if fails:
    raise SystemExit(1)
