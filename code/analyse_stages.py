#!/usr/bin/env python3
"""Frozen analysis for the preregistered run R8, the attraction law across the stages of post-training (addendum of 2 November 2026).

    python3 -I code/analyse_stages.py --instruct A.json --sft B.json --dpo C.json --rlvr D.json [--json OUT]
    python3 -I code/analyse_stages.py --selftest

Each file has the schema of code/analyse_runs.py (arms critical and praise, same items, same K) and holds one
post-trained version of Llama-3.1-8B at the standard dose: Llama-3.1-8B-Instruct (reused from R6) and the three
Tulu 3 stages SFT, DPO, RLVR. The four files must hold the same items.

Per stage: the frozen analysis of analyse_runs.py (g, c, intervals, nulls, criteria, regime).
Across stages, per arm, with one paired item bootstrap (the same item draws at every stage, B = 10 000):
  g and c differences for the Tulu steps sft->dpo and dpo->rlvr, and for rlvr - instruct, each with a 95 % percentile
  interval. Attraction in an arm at a stage: the 95 % interval of g lies above 0.

Hypotheses (fixed in the addendum before any data; every test is two-sided through its interval):
  S1 not specific to Meta's post-training: C1 holds at rlvr.
  S2 installed by imitation: C1 holds at sft.
  S3 preference optimisation lowers the gain: the interval of g(dpo) - g(sft) lies below 0 in at least one arm, and the
     interval of g(rlvr) - g(dpo) includes 0 in both arms.
  S4 destination stable across stages: in each arm, at every Tulu step where both ends show attraction, the interval of
     c(stage) - c(previous) includes 0. Not applicable in an arm without attraction at one end of a step.
  S5 (descriptive) same base, same destinations: the intervals of c(rlvr) - c(instruct) include 0 in both arms, and C2
     holds at rlvr.
Outcomes: A = S1 and S2 and S4; B = S1 and not S2; C = not S1. S3 and S5 are reported beside the outcome.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("analyse_runs", HERE / "analyse_runs.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
rp = ar.rp

SEED = 20261102
STAGES = ("instruct", "sft", "dpo", "rlvr")
STEPS = (("sft", "dpo"), ("dpo", "rlvr"), ("instruct", "rlvr"))
ARMS = ("critical", "praise")
PREDICTION = "S1, S2 and S4 (outcome A); S3 per the author's prior; S5 descriptive"


def attracts(stage_result, arm):
    return bool(stage_result["arms"][arm]["g_ci95"][0] > 0)


def includes0(iv):
    return bool(np.isfinite(iv).all() and iv[0] <= 0 <= iv[1])


def stages(data_by_stage, per_stage):
    """Paired item bootstrap across the four stages, per arm."""
    out = {}
    children = np.random.SeedSequence(SEED, spawn_key=(8,)).spawn(2)
    for arm, child in zip(ARMS, children):
        rng = np.random.default_rng(child)
        n = data_by_stage["instruct"][arm][0].shape[0]
        idx = rng.integers(0, n, size=(rp.B_BOOT, n))
        gb, cb = {}, {}
        for st in STAGES:
            neu, pre = data_by_stage[st][arm]
            gb[st], cb[st] = rp.ols(neu.mean(1)[idx], pre.mean(1)[idx])
        a = {"g": {st: [per_stage[st]["arms"][arm]["g"], per_stage[st]["arms"][arm]["g_ci95"]] for st in STAGES},
             "c": {st: [per_stage[st]["arms"][arm]["c"], per_stage[st]["arms"][arm]["c_ci95"]] for st in STAGES},
             "attraction": {st: attracts(per_stage[st], arm) for st in STAGES}, "g_diff": {}, "c_diff": {}}
        for lo, hi in STEPS:
            key = f"{hi}-{lo}"
            a["g_diff"][key] = [float(per_stage[hi]["arms"][arm]["g"] - per_stage[lo]["arms"][arm]["g"]), rp.ci95(gb[hi] - gb[lo])]
            dc = cb[hi] - cb[lo]
            dc = dc[np.isfinite(dc)]
            a["c_diff"][key] = [float(per_stage[hi]["arms"][arm]["c"] - per_stage[lo]["arms"][arm]["c"]),
                                rp.ci95(dc) if len(dc) else [float("nan"), float("nan")], int(rp.B_BOOT - len(dc))]
        out[arm] = a
    return out


def hypotheses(per_stage, d):
    s1 = bool(per_stage["rlvr"]["criteria"]["C1_attraction"])
    s2 = bool(per_stage["sft"]["criteria"]["C1_attraction"])
    s3 = bool(any(d[arm]["g_diff"]["dpo-sft"][1][1] < 0 for arm in ARMS) and all(includes0(d[arm]["g_diff"]["rlvr-dpo"][1]) for arm in ARMS))
    s4_arms = {}
    for arm in ARMS:
        tests = []
        for lo, hi in (("sft", "dpo"), ("dpo", "rlvr")):
            if d[arm]["attraction"][lo] and d[arm]["attraction"][hi]:
                tests.append(includes0(d[arm]["c_diff"][f"{hi}-{lo}"][1]))
        s4_arms[arm] = (all(tests) if tests else None)
    applicable = [v for v in s4_arms.values() if v is not None]
    s4 = (all(applicable) if applicable else None)
    s5 = bool(all(includes0(d[arm]["c_diff"]["rlvr-instruct"][1]) for arm in ARMS) and per_stage["rlvr"]["criteria"]["C2_two_destinations"])
    return {"S1_attraction_at_rlvr": s1, "S2_attraction_at_sft": s2, "S3_dpo_lowers_gain": s3, "S4_destination_stable": s4,
            "S4_per_arm": s4_arms, "S5_same_destinations_as_instruct": s5}


def outcome(h):
    if not h["S1_attraction_at_rlvr"]:
        return "C: no two-sided attraction at the final Tulu stage; the law is specific to Meta's post-training at this dose"
    if not h["S2_attraction_at_sft"]:
        return "B: the attraction appears after supervised fine-tuning, at DPO or RLVR: preference optimisation installs it"
    if h["S4_destination_stable"]:
        return "A: the attraction is present from supervised fine-tuning on, and later stages move the gain, not the destination"
    if h["S4_destination_stable"] is None:
        return "S1 and S2 hold; S4 not applicable (no step with attraction at both ends in either arm): reported as such"
    return "S1 and S2 hold but S4 fails: present from SFT on, with a destination that moves between stages; reported as such"


def run(paths, oos):
    per_stage, data_by_stage, items0, sha = {}, {}, None, {}
    for st in STAGES:
        meta, items, data = ar.load(paths[st])
        if items0 is None:
            items0 = items
        elif items != items0:
            rp.fail(f"{st}: items differ from those of the instruct file")
        per_stage[st] = ar.analyse(data, oos=oos)
        data_by_stage[st] = data
        sha[st] = hashlib.sha256(Path(paths[st]).read_bytes()).hexdigest()
    d = stages(data_by_stage, per_stage)
    h = hypotheses(per_stage, d)
    return {"meta": {"run": "R8", "prediction": PREDICTION, "inputs": {st: str(paths[st]) for st in STAGES}, "inputs_sha256": sha,
                     "items": len(items0), "oos": oos},
            "stages": per_stage, "comparison": d, "hypotheses": h, "outcome": outcome(h)}


def report(res):
    f = lambda x: f"{x:.3f}"
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"R8 post-training stages · prediction {res['meta']['prediction']} · {res['meta']['items']} items")
    for st in STAGES:
        a = res["stages"][st]
        print(f"  {st:<9} " + " · ".join(f"{arm} g={f(a['arms'][arm]['g'])} {iv(a['arms'][arm]['g_ci95'])} c={f(a['arms'][arm]['c'])} {iv(a['arms'][arm]['c_ci95'])}" for arm in ARMS)
              + f" · C1={a['criteria']['C1_attraction']} C2={a['criteria']['C2_two_destinations']} regime={a['regime']}")
    for arm in ARMS:
        d = res["comparison"][arm]
        print(f"  {arm:<9} " + " · ".join(f"g({hi})-g({lo})={d['g_diff'][f'{hi}-{lo}'][0]:+.3f} {iv(d['g_diff'][f'{hi}-{lo}'][1])}" for lo, hi in STEPS))
        print(f"  {'':<9} " + " · ".join(f"c({hi})-c({lo})={d['c_diff'][f'{hi}-{lo}'][0]:+.3f} {iv(d['c_diff'][f'{hi}-{lo}'][1])}" for lo, hi in STEPS))
    h = res["hypotheses"]
    print("  hypotheses: " + " · ".join(f"{k}={v}" for k, v in h.items() if k.startswith("S")))
    print(f"  outcome: {res['outcome']}")


def selftest():
    """Four simulated stages with fixed targets and gains 0.7 (instruct), 0.7 (sft), 0.45 (dpo), 0.45 (rlvr): S1, S2, S3, S4,
    S5 and outcome A are expected."""
    rng = np.random.default_rng(SEED)
    paths = {}
    for st, g in zip(STAGES, (0.7, 0.7, 0.45, 0.45)):
        p0_true = rng.uniform(1.2, 4.6, 40)
        arms = {}
        for arm, c in (("critical", 1.3), ("praise", 3.5)):
            draw = lambda m: np.clip(np.rint(m[:, None] + rng.normal(0, 0.6, (40, 5))), 1, 5)
            neu, pre = draw(p0_true), draw(p0_true + g * (c - p0_true))
            arms[arm] = {str(i): {"neutral": neu[i].tolist(), "pressure": pre[i].tolist()} for i in range(40)}
        paths[st] = HERE / f".selftest_stages_{st}.json"
        paths[st].write_text(json.dumps({"meta": {"run": f"selftest-{st}"}, "arms": arms}))
    rp.B_PERM = 4_000
    res = run(paths, oos=False)
    for p in paths.values():
        p.unlink()
    report(res)
    h = res["hypotheses"]
    ok = bool(h["S1_attraction_at_rlvr"] and h["S2_attraction_at_sft"] and h["S3_dpo_lowers_gain"] and h["S4_destination_stable"]
              and h["S5_same_destinations_as_instruct"] and res["outcome"].startswith("A"))
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for st in STAGES:
        ap.add_argument(f"--{st}")
    ap.add_argument("--oos", action="store_true", help="also report C3 and C4 against the campaign-1 law at every stage (descriptive)")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not all(getattr(args, st) for st in STAGES):
        ap.error("the four input files are required")
    res = run({st: Path(getattr(args, st)) for st in STAGES}, args.oos)
    report(res)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
