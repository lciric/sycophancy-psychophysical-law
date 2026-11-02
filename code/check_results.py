"""Recompute every published follow-up result from its public input with the frozen analysis, and compare.

For each results/**/*_input_*.json, runs code/analyse_runs.py on it (with --oos when the input's meta has "oos": true)
and checks that the 'analysis' section equals the one in the matching *_output_*.json, value for value. For each
results/**/*_dose_output.json, reruns code/analyse_dose.py on the inputs its meta names and checks levels, dose,
hypotheses and outcome; likewise *_stages_output.json with code/analyse_stages.py and *_fsec_output.json with
code/analyse_fsec.py. Exit status 1 on any difference or missing file.
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
    extra = ["--oos"] if json.loads(inp.read_text()).get("meta", {}).get("oos") is True else []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.json"
        subprocess.run([sys.executable, "-I", "-B", str(ROOT / "code" / "analyse_runs.py"), str(inp), *extra, "--json", str(tmp_out)],
                       check=True, capture_output=True, text=True)
        same = json.loads(tmp_out.read_text())["analysis"] == json.loads(out.read_text())["analysis"]
    print(("OK       " if same else "DIFFERS  ") + str(out.relative_to(ROOT)))
    bad += not same
doses = sorted(ROOT.glob("results/**/*_dose_output.json"))
for out in doses:
    ref = json.loads(out.read_text())
    m = ref["meta"]
    args = [sys.executable, "-I", "-B", str(ROOT / "code" / "analyse_dose.py"), "--family", m["family"]]
    for lev in ("mild", "standard", "strong"):
        args += [f"--{lev}", m["inputs"][lev]]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.json"
        subprocess.run(args + (["--oos"] if m.get("oos") else []) + ["--json", str(tmp_out)], cwd=ROOT, check=True, capture_output=True, text=True)
        new = json.loads(tmp_out.read_text())
    same = all(new[k] == ref[k] for k in ("levels", "dose", "hypotheses", "outcome"))
    print(("OK       " if same else "DIFFERS  ") + str(out.relative_to(ROOT)))
    bad += not same
stage_outs = sorted(ROOT.glob("results/**/*_stages_output.json"))
for out in stage_outs:
    ref = json.loads(out.read_text())
    args = [sys.executable, "-I", "-B", str(ROOT / "code" / "analyse_stages.py")]
    for st in ("instruct", "sft", "dpo", "rlvr"):
        args += [f"--{st}", ref["meta"]["inputs"][st]]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.json"
        subprocess.run(args + (["--oos"] if ref["meta"].get("oos") else []) + ["--json", str(tmp_out)], cwd=ROOT, check=True, capture_output=True, text=True)
        new = json.loads(tmp_out.read_text())
    same = all(new[k] == ref[k] for k in ("stages", "comparison", "hypotheses", "outcome"))
    print(("OK       " if same else "DIFFERS  ") + str(out.relative_to(ROOT)))
    bad += not same
fsec_outs = sorted(ROOT.glob("results/**/*_fsec_output.json"))
for out in fsec_outs:
    ref = json.loads(out.read_text())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_out = Path(tmp) / "out.json"
        subprocess.run([sys.executable, "-I", "-B", str(ROOT / "code" / "analyse_fsec.py"), ref["meta"]["input"], "--json", str(tmp_out)], cwd=ROOT, check=True, capture_output=True, text=True)
        new = json.loads(tmp_out.read_text())
    same = all(new[k] == ref[k] for k in ("directions", "pairs", "behaviour", "hypotheses", "outcome"))
    print(("OK       " if same else "DIFFERS  ") + str(out.relative_to(ROOT)))
    bad += not same
if bad:
    sys.exit(f"CHECK FAILED: {bad} result(s) differ or are missing")
print(f"CHECK PASSED: {len(inputs)} published result(s), {len(doses)} dose-response, {len(stage_outs)} stage and {len(fsec_outs)} error-correction result(s) recomputed from their inputs")
