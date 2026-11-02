"""Recompute every published follow-up result from its public input with the frozen analysis, and compare.

For each results/**/*_input_*.json, runs code/analyse_runs.py on it and checks that the 'analysis' section equals the
one in the matching *_output_*.json, value for value. Exit status 1 on any difference or missing file.
Usage: python3 -I code/check_results.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
inputs = sorted(ROOT.glob("results/**/*_input_*.json"))
if not inputs:
    sys.exit("no published input found under results/")
bad = 0
for inp in inputs:
    out = inp.with_name(inp.name.replace("_input_", "_output_"))
    if not out.exists():
        print(f"MISSING  {out.relative_to(ROOT)}")
        bad += 1
        continue
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.json"
        subprocess.run([sys.executable, "-I", "-B", str(ROOT / "code" / "analyse_runs.py"), str(inp), "--json", str(tmp_out)],
                       check=True, capture_output=True, text=True)
        same = json.loads(tmp_out.read_text())["analysis"] == json.loads(out.read_text())["analysis"]
    print(("OK       " if same else "DIFFERS  ") + str(out.relative_to(ROOT)))
    bad += not same
if bad:
    sys.exit(f"CHECK FAILED: {bad} result(s) differ or are missing")
print(f"CHECK PASSED: {len(inputs)} published result(s) recomputed from their inputs")
