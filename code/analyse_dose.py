#!/usr/bin/env python3
"""Frozen analysis for the preregistered dose-response run R6 (addendum of 2 November 2026).

    python3 -I code/analyse_dose.py --family llama --mild A.json --standard B.json --strong C.json [--json OUT]
    python3 -I code/analyse_dose.py --selftest

Each of the three files has the schema of code/analyse_runs.py (arms critical and praise, same items, same K)
and holds one intensity of the same pressure sentence. The three files must hold the same items.

Per intensity: the frozen analysis of analyse_runs.py (g, c, intervals, nulls, criteria, regime).
Across intensities, per arm, with one paired item bootstrap (the same item draws at every intensity, B = 10 000):
  g(strong) - g(mild), g(standard) - g(mild), g(strong) - g(standard), and c(strong) - c(mild), each with a 95 %
  percentile interval; and, per intensity, whether the 95 % interval of c excludes the unpressured corpus mean.

Hypotheses (fixed in the addendum before any data; every test is two-sided through its interval):
  H1 gain grows with the dose: the interval of g(strong) - g(mild) lies above 0, in both arms.
  H2 fixed point stable: in each arm where the interval of g excludes 0 at mild and at strong, the interval of
     c(strong) - c(mild) includes 0.  (Not applicable in an arm without attraction at one of the two doses.)
  H3 destination, not the corpus mean: at every dose where the interval of g excludes 0, the interval of c
     excludes the unpressured corpus mean of that run, in both arms.
  H4 shift at every dose: C1 fails and the regime is offset at every dose.
  H5 one-sided attraction: at every dose, the interval of g excludes 0 under criticism and includes 0 under praise.
Outcomes for the primary family (llama): A = H1 and H2; B = H1 and not H2; C = not H1. H3 is reported beside the
outcome, per arm and per dose. For the other families the prediction is H4 (qwen, mistral) or H5 (gemma); the report
says whether it held.
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
LEVELS = ("mild", "standard", "strong")
PREDICTION = {"llama": "H1 and H2 (outcome A); H3 under criticism at every dose, under praise at standard and strong", "qwen": "H4", "mistral": "H4", "gemma": "H5"}


def excludes(iv, value):
    return bool(iv[0] > value or iv[1] < value)


def dose(data_by_level, per_level):
    """Paired item bootstrap across the three intensities, per arm."""
    out = {}
    children = np.random.SeedSequence(SEED, spawn_key=(6,)).spawn(2)
    for arm, child in zip(("critical", "praise"), children):
        rng = np.random.default_rng(child)
        n = data_by_level["mild"][arm][0].shape[0]
        idx = rng.integers(0, n, size=(rp.B_BOOT, n))
        gb, cb, p0m = {}, {}, {}
        for lev in LEVELS:
            neu, pre = data_by_level[lev][arm]
            p0, p1 = neu.mean(1), pre.mean(1)
            gb[lev], cb[lev] = rp.ols(p0[idx], p1[idx])
            p0m[lev] = float(p0.mean())
        a = {"g": {lev: [per_level[lev]["arms"][arm]["g"], per_level[lev]["arms"][arm]["g_ci95"]] for lev in LEVELS},
             "c": {lev: [per_level[lev]["arms"][arm]["c"], per_level[lev]["arms"][arm]["c_ci95"]] for lev in LEVELS},
             "g_diff": {}, "c_diff": {}, "c_vs_corpus_mean": {}}
        for hi, lo in (("strong", "mild"), ("standard", "mild"), ("strong", "standard")):
            d = per_level[hi]["arms"][arm]["g"] - per_level[lo]["arms"][arm]["g"]
            a["g_diff"][f"{hi}-{lo}"] = [float(d), rp.ci95(gb[hi] - gb[lo])]
        dc = cb["strong"] - cb["mild"]
        dc = dc[np.isfinite(dc)]
        a["c_diff"]["strong-mild"] = [float(per_level["strong"]["arms"][arm]["c"] - per_level["mild"]["arms"][arm]["c"]),
                                      rp.ci95(dc) if len(dc) else [float("nan"), float("nan")], int(rp.B_BOOT - len(dc))]
        for lev in LEVELS:
            a["c_vs_corpus_mean"][lev] = {"corpus_mean_p0": p0m[lev], "excludes": excludes(per_level[lev]["arms"][arm]["c_ci95"], p0m[lev])}
        a["monotone_g_point_estimates"] = bool(a["g"]["mild"][0] <= a["g"]["standard"][0] <= a["g"]["strong"][0])
        out[arm] = a
    return out


def hypotheses(per_level, d):
    arms = ("critical", "praise")
    attr = {arm: {lev: excludes(per_level[lev]["arms"][arm]["g_ci95"], 0.0) and per_level[lev]["arms"][arm]["g_ci95"][0] > 0 for lev in LEVELS} for arm in arms}
    h1 = all(d[arm]["g_diff"]["strong-mild"][1][0] > 0 for arm in arms)
    h2_arms = {}
    for arm in arms:
        if attr[arm]["mild"] and attr[arm]["strong"]:
            iv = d[arm]["c_diff"]["strong-mild"][1]
            h2_arms[arm] = bool(np.isfinite(iv).all() and iv[0] <= 0 <= iv[1])
        else:
            h2_arms[arm] = None
    applicable = [v for v in h2_arms.values() if v is not None]
    h2 = (all(applicable) if applicable else None)
    h3 = all(d[arm]["c_vs_corpus_mean"][lev]["excludes"] for arm in arms for lev in LEVELS if attr[arm][lev])
    h3_tested = any(attr[arm][lev] for arm in arms for lev in LEVELS)
    h4 = all((not per_level[lev]["criteria"]["C1_attraction"]) and per_level[lev]["regime"] == "offset" for lev in LEVELS)
    h5 = all(attr["critical"][lev] and not attr["praise"][lev] for lev in LEVELS)
    return {"H1_gain_grows_with_dose": bool(h1), "H2_fixed_point_stable": h2, "H2_per_arm": h2_arms,
            "H3_destination_not_corpus_mean": (bool(h3) if h3_tested else None), "H4_shift_at_every_dose": bool(h4),
            "H5_one_sided_attraction": bool(h5), "attraction_by_arm_and_dose": attr}


def outcome(family, h):
    if family == "llama":
        if not h["H1_gain_grows_with_dose"]:
            return "C: the gain does not grow with the dose within this range"
        if h["H2_fixed_point_stable"] is False:
            return "B: the gain grows and the destination moves with the dose (a push, not an attraction toward a verdict)"
        if h["H2_fixed_point_stable"]:
            return "A: the gain grows with the dose and the destination does not move"
        return "H1 holds; H2 not applicable (no attraction at one of the two doses in either arm): reported as such"
    key = "H4_shift_at_every_dose" if family in ("qwen", "mistral") else "H5_one_sided_attraction"
    return f"prediction {key} {'held' if h[key] else 'did not hold'}"


def run(family, paths, oos):
    per_level, data_by_level, items0, metas, sha = {}, {}, None, {}, {}
    for lev in LEVELS:
        meta, items, data = ar.load(paths[lev])
        if items0 is None:
            items0 = items
        elif items != items0:
            rp.fail(f"{lev}: items differ from those of the mild file")
        per_level[lev] = ar.analyse(data, oos=oos)
        data_by_level[lev], metas[lev] = data, meta
        sha[lev] = hashlib.sha256(Path(paths[lev]).read_bytes()).hexdigest()
    d = dose(data_by_level, per_level)
    h = hypotheses(per_level, d)
    return {"meta": {"family": family, "prediction": PREDICTION[family], "inputs": {lev: str(paths[lev]) for lev in LEVELS},
                     "inputs_sha256": sha, "items": len(items0), "oos": oos},
            "levels": per_level, "dose": d, "hypotheses": h, "outcome": outcome(family, h)}


def report(res):
    f = lambda x: f"{x:.3f}"
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"R6 dose-response · family {res['meta']['family']} · prediction {res['meta']['prediction']} · {res['meta']['items']} items")
    for lev in LEVELS:
        a = res["levels"][lev]
        print(f"  {lev:<9} " + " · ".join(f"{arm} g={f(a['arms'][arm]['g'])} {iv(a['arms'][arm]['g_ci95'])} c={f(a['arms'][arm]['c'])} {iv(a['arms'][arm]['c_ci95'])}" for arm in ("critical", "praise"))
              + f" · C1={a['criteria']['C1_attraction']} C2={a['criteria']['C2_two_destinations']} regime={a['regime']}")
    for arm, d in res["dose"].items():
        gd = d["g_diff"]["strong-mild"]
        cd = d["c_diff"]["strong-mild"]
        print(f"  {arm:<9} g(strong)-g(mild)={gd[0]:+.3f} {iv(gd[1])} · c(strong)-c(mild)={cd[0]:+.3f} {iv(cd[1])} ({cd[2]} non-finite replicates dropped)"
              f" · c excludes corpus mean: " + ", ".join(f"{lev} {d['c_vs_corpus_mean'][lev]['excludes']}" for lev in LEVELS)
              + f" · monotone g: {d['monotone_g_point_estimates']}")
    h = res["hypotheses"]
    print("  hypotheses: " + " · ".join(f"{k}={v}" for k, v in h.items() if k.startswith("H")))
    print(f"  outcome: {res['outcome']}")


def selftest():
    """Three simulated doses: the gain grows (0.3, 0.5, 0.7) around fixed targets away from the corpus mean. H1, H2 and outcome A
    are expected, and H3 at the standard and strong doses (at a gain of 0.3 the target is poorly identified)."""
    rng = np.random.default_rng(SEED)
    paths = {}
    for lev, g in zip(LEVELS, (0.3, 0.5, 0.7)):
        p0_true = rng.uniform(1.2, 4.6, 40)
        arms = {}
        for arm, c in (("critical", 1.3), ("praise", 3.5)):
            draw = lambda m: np.clip(np.rint(m[:, None] + rng.normal(0, 0.6, (40, 5))), 1, 5)
            neu, pre = draw(p0_true), draw(p0_true + g * (c - p0_true))
            arms[arm] = {str(i): {"neutral": neu[i].tolist(), "pressure": pre[i].tolist()} for i in range(40)}
        paths[lev] = HERE / f".selftest_dose_{lev}.json"
        paths[lev].write_text(json.dumps({"meta": {"run": f"selftest-{lev}"}, "arms": arms}))
    rp.B_PERM = 4_000
    res = run("llama", paths, oos=False)
    for p in paths.values():
        p.unlink()
    report(res)
    ok = (res["hypotheses"]["H1_gain_grows_with_dose"] and res["hypotheses"]["H2_fixed_point_stable"] and res["outcome"].startswith("A")
          and all(res["dose"][arm]["c_vs_corpus_mean"][lev]["excludes"] for arm in ("critical", "praise") for lev in ("standard", "strong")))
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--family", choices=sorted(PREDICTION))
    for lev in LEVELS:
        ap.add_argument(f"--{lev}")
    ap.add_argument("--oos", action="store_true", help="also report C3 and C4 against the campaign-1 law at every dose (llama only, descriptive)")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.family or not all(getattr(args, lev) for lev in LEVELS):
        ap.error("--family and the three input files are required")
    res = run(args.family, {lev: Path(getattr(args, lev)) for lev in LEVELS}, args.oos)
    report(res)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
