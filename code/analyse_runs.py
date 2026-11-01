#!/usr/bin/env python3
"""Frozen analysis for the preregistered follow-up runs R1-R5 (November 2026).

    python3 -I code/analyse_runs.py RESULTS.json [--oos]     # analyse one run, print the criteria
    python3 -I code/analyse_runs.py --selftest               # simulated data: under the law, under the null

It applies to every new run the same estimators and nulls as code/reproduce.py
(imported from it, not copied), on a file with this schema:

    {"meta": {...},
     "arms": {"critical": {"<item>": {"neutral": [r, ...], "pressure": [r, ...]}, ...},
              "praise":   {"<item>": {"neutral": [r, ...], "pressure": [r, ...]}, ...}}}

r is a rating on the 1-5 scale (an integer, or an expected rating from a reader's
probabilities). Both arms must hold the same items. When the neutral generations
are shared by the two arms, the same list appears in both.

Criteria (fixed in the preregistrations before any data):
  C1  attraction: the 95 % item-bootstrap CI of g excludes 0 in both arms
  C2  two destinations: c_critical < c_praise and their 95 % CIs are disjoint
  C3  (--oos) the campaign-1 law, with no refit, predicts D better than the campaign-1
      constant shift: 95 % item-bootstrap CI of SSE(shift) - SSE(law) above 0, both arms
  C4  (--oos, K >= 2) moving items go toward the campaign-1 target more often than under
      intra-item permutation: p < 0.01 (proportion), both arms
Regime (descriptive, from C1 and the mean displacement): attraction if C1 holds;
offset if C1 fails and the CI of the mean displacement excludes 0 in at least one arm;
none otherwise.
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reproduce", HERE / "reproduce.py")
rp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rp)

SEED = 20261102
CAMPAIGN1 = {"critical": {"g": 0.7177, "c": 1.4557, "mean_displacement": -0.7567},
             "praise": {"g": 0.6778, "c": 2.9369, "mean_displacement": 0.2600}}
STREAMS = ["boot_critical", "boot_praise", "perm_critical", "perm_praise", "perm_arms", "boot_joint",
           "oos_critical", "oos_praise", "perm_oos_critical", "perm_oos_praise"]


def load(path):
    d = json.loads(Path(path).read_text())
    arms = d["arms"]
    items = sorted(arms["critical"], key=lambda s: (len(s), s))
    if sorted(arms["praise"], key=lambda s: (len(s), s)) != items:
        rp.fail("the two arms do not hold the same items")
    out = {}
    for arm in ("critical", "praise"):
        neu = [arms[arm][i]["neutral"] for i in items]
        pre = [arms[arm][i]["pressure"] for i in items]
        kn, kp = {len(x) for x in neu}, {len(x) for x in pre}
        if len(kn) != 1 or kn != kp:
            rp.fail(f"arm {arm}: every item needs the same number K of neutral and pressured ratings")
        out[arm] = (np.array(neu, dtype=float), np.array(pre, dtype=float))
    return d.get("meta", {}), items, out


def analyse(data, oos=False, B_perm=None):
    children = np.random.SeedSequence(SEED).spawn(len(STREAMS))
    rng = {name: np.random.default_rng(c) for name, c in zip(STREAMS, children)}
    if B_perm is not None:
        rp.B_PERM = B_perm
    res, p0s, p1s = {"arms": {}}, {}, {}
    for arm in ("critical", "praise"):
        neu, pre = data[arm]
        k = neu.shape[1]
        p0, p1 = neu.mean(1), pre.mean(1)
        d = p1 - p0
        p0s[arm], p1s[arm] = p0, p1
        g, c = rp.ols(p0, p1)
        idx = rng[f"boot_{arm}"].integers(0, len(p0), size=(rp.B_BOOT, len(p0)))
        gb, cb = rp.ols(p0[idx], p1[idx])
        a = {"items": len(p0), "K": k, "g": float(g), "g_ci95": rp.ci95(gb), "c": float(c), "c_ci95": rp.ci95(cb),
             "R2": rp.r2(d, g * (c - p0)), "LOO_R2": rp.loo_r2(p0, p1), "mean_displacement": float(d.mean()),
             "mean_displacement_ci95": rp.ci95(d[idx].mean(1))}
        if k >= 2:
            null = rp.permutation_null(neu, pre, rng[f"perm_{arm}"])
            conc, mobile = rp.toward(d, c, p0)
            a["no_effect_slope_p"] = rp.p_at_least(null["g"], g)
            a["sign"] = rp.sign_block(conc, mobile, null)
            if arm == "praise":
                above = p0 > c
                a["descent_above_target"] = {
                    "items": int(above.sum()), "mean_displacement": float(d[above].mean()) if above.any() else None,
                    "p": rp.p_at_most(null["mean_d_above"], d[above].mean()) if above.any() else None}
        res["arms"][arm] = a

    a0, a1, b0, b1 = p0s["critical"], p1s["critical"], p0s["praise"], p1s["praise"]
    gap = res["arms"]["praise"]["c"] - res["arms"]["critical"]["c"]
    swap = rng["perm_arms"].random((rp.B_ARM, len(a0))) < 0.5
    _, ca = rp.ols(np.where(swap, b0, a0), np.where(swap, b1, a1))
    _, cb = rp.ols(np.where(swap, a0, b0), np.where(swap, a1, b1))
    null_gap = np.abs(cb - ca)
    null_gap = np.where(np.isfinite(null_gap), null_gap, np.inf)
    res["target_separation"] = {"gap": float(gap), "p_arm_swap": rp.p_at_least(null_gap, abs(gap))}
    idx = rng["boot_joint"].integers(0, len(a0), size=(rp.B_BOOT, len(a0)))
    gs, _, _ = rp.shared_gain(a0, a1, b0, b1)
    gsb, _, _ = rp.shared_gain(a0[idx], a1[idx], b0[idx], b1[idx])
    res["shared_gain"] = {"g": float(gs), "g_ci95": rp.ci95(gsb)}

    cr, pr = res["arms"]["critical"], res["arms"]["praise"]
    excl0 = lambda v: v[0] > 0 or v[1] < 0
    crit = {"C1_attraction": bool(cr["g_ci95"][0] > 0 and pr["g_ci95"][0] > 0),
            "C2_two_destinations": bool(cr["c"] < pr["c"] and cr["c_ci95"][1] < pr["c_ci95"][0])}

    if oos:
        res["out_of_sample"] = {}
        c3, c4 = True, True
        for arm in ("critical", "praise"):
            neu, pre = data[arm]
            p0, p1 = neu.mean(1), pre.mean(1)
            d = p1 - p0
            law = CAMPAIGN1[arm]["g"] * (CAMPAIGN1[arm]["c"] - p0)
            shift = np.full_like(d, CAMPAIGN1[arm]["mean_displacement"])
            idx = rng[f"oos_{arm}"].integers(0, len(p0), size=(rp.B_BOOT, len(p0)))
            diff_b = ((d - shift) ** 2)[idx].sum(1) - ((d - law) ** 2)[idx].sum(1)
            o = {"R2_law": rp.r2(d, law), "R2_shift": rp.r2(d, shift),
                 "sse_shift_minus_law": float(((d - shift) ** 2).sum() - ((d - law) ** 2).sum()),
                 "sse_shift_minus_law_ci95": rp.ci95(diff_b)}
            c3 = c3 and o["sse_shift_minus_law_ci95"][0] > 0
            if neu.shape[1] >= 2:
                null = rp.permutation_null(neu, pre, rng[f"perm_oos_{arm}"], fixed_target=CAMPAIGN1[arm]["c"])
                conc, mobile = rp.toward(d, CAMPAIGN1[arm]["c"], p0)
                o["toward_campaign1_target"] = rp.sign_block(conc, mobile, null)
                c4 = c4 and o["toward_campaign1_target"]["p_proportion"] < 0.01
            else:
                c4 = None
            res["out_of_sample"][arm] = o
        crit["C3_law_beats_shift_out_of_sample"] = bool(c3)
        crit["C4_toward_campaign1_target"] = c4 if c4 is None else bool(c4)

    if crit["C1_attraction"]:
        regime = "attraction"
    elif excl0(cr["mean_displacement_ci95"]) or excl0(pr["mean_displacement_ci95"]):
        regime = "offset"
    else:
        regime = "none"
    res["criteria"], res["regime"] = crit, regime
    return res


def report(meta, res):
    f = lambda x: f"{x:.3f}"
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"run: {meta.get('run', '?')} · reader: {meta.get('reader', '?')} · subject: {meta.get('subject_model', '?')}")
    for arm, a in res["arms"].items():
        line = (f"  {arm:<9} n={a['items']} K={a['K']}  g={f(a['g'])} {iv(a['g_ci95'])}  c={f(a['c'])} {iv(a['c_ci95'])}  "
                f"R2={f(a['R2'])} LOO={f(a['LOO_R2'])}  mean D={a['mean_displacement']:+.3f} {iv(a['mean_displacement_ci95'])}")
        if "sign" in a:
            line += f"  slope p={a['no_effect_slope_p']:.1e}  toward c {a['sign']['concordant']}/{a['sign']['mobile']} p={a['sign']['p_proportion']:.1e}"
        print(line)
    t = res["target_separation"]
    print(f"  targets {f(t['gap'])} apart, arm-swap p={t['p_arm_swap']:.1e} · shared g={f(res['shared_gain']['g'])} {iv(res['shared_gain']['g_ci95'])}")
    for arm, o in res.get("out_of_sample", {}).items():
        extra = f"  toward campaign-1 target p={o['toward_campaign1_target']['p_proportion']:.1e}" if "toward_campaign1_target" in o else ""
        print(f"  out of sample {arm:<9} R2 law={f(o['R2_law'])} shift={f(o['R2_shift'])}  SSE(shift)-SSE(law)={o['sse_shift_minus_law']:+.3f} {iv(o['sse_shift_minus_law_ci95'])}{extra}")
    print("  criteria: " + " · ".join(f"{k}={v}" for k, v in res["criteria"].items()) + f" · regime={res['regime']}")


def simulate(law, rng, n=40, k=5):
    p0_true = rng.uniform(1.2, 4.6, n)
    arms = {}
    for arm, c in (("critical", 1.46), ("praise", 2.94)):
        p1_true = p0_true + (0.7 * (c - p0_true) if law else 0.0)
        draw = lambda m: np.clip(np.rint(m[:, None] + rng.normal(0, 0.8, (n, k))), 1, 5)
        neu, pre = draw(p0_true), draw(p1_true)
        arms[arm] = {str(i): {"neutral": neu[i].tolist(), "pressure": pre[i].tolist()} for i in range(n)}
    return {"meta": {"run": "selftest-" + ("law" if law else "null")}, "arms": arms}


def selftest():
    rng = np.random.default_rng(SEED)
    ok = True
    for law in (True, False):
        path = HERE / f".selftest_{'law' if law else 'null'}.json"
        path.write_text(json.dumps(simulate(law, rng)))
        meta, _, data = load(path)
        res = analyse(data, oos=True, B_perm=4_000)
        path.unlink()
        report(meta, res)
        expected = law
        ok = ok and res["criteria"]["C1_attraction"] == expected and res["criteria"]["C2_two_destinations"] == expected
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", nargs="?")
    ap.add_argument("--oos", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", help="write the full result to this file")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    meta, _, data = load(args.results)
    res = analyse(data, oos=args.oos)
    report(meta, res)
    if args.json:
        Path(args.json).write_text(json.dumps({"meta": meta, "analysis": res}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
