#!/usr/bin/env python3
"""Frozen analysis for the preregistered run R9: is the pressure direction a feature, by the error-correction test of
Ferreira da Silva & Heimersheim (2026), "Evidence for feature-specific error correction in LLMs" (arXiv 2606.24964)?

    python3 -I code/analyse_fsec.py INPUT.json [--json OUT]
    python3 -I code/analyse_fsec.py --selftest

INPUT.json (built by the run from the outputs of the FSEC pipeline, github.com/FranciscoHS/fsec-paper):
  angles_deg: the rotation angles of the sweep (ascending, from 0).
  directions: {name: {family, l2}} with family in {pressure_critical, pressure_praise, contrastive, randomdiff, random, pca}
              and l2 the per-anchor response curves, a list of n_anchors lists of len(angles_deg) values (L2 at the
              read-out layer between the perturbed and the unperturbed activation, FineWeb anchors).
  pairs: [{d1, d2, p, p_ci95}], the superellipse exponent fitted by the pipeline (per-pair threshold, exact geodesic) for
         every pair with |cos| < 0.1 between a direction of family pressure_* or randomdiff and a contrastive direction.
  behaviour: {name: {expected_rating}} for the two pressure directions and the randomdiff directions: per rating-prompt
             anchor, the expected rating sum_k k p(k) over the tokens "1"-"5" at each angle (list of lists).

Statistics (every interval is a 95 % percentile bootstrap, B = 10 000, seed 20261102):
  threshold T = 0.5 x the median, over the randomdiff directions, of the maximum of their anchor-median curve;
  break angle of a direction = the smallest angle at which its anchor-median curve exceeds T (the last angle if never);
  F1 sensitive: for each pressure direction, the anchor-bootstrap interval of its break angle minus the median break
     angle of the randomdiff directions lies below 0;
  F2 feature-specific: the lower bound of the partner-bootstrap interval of the median p over (pressure, contrastive)
     pairs lies above 2.05 and above the upper bound of the same interval over (randomdiff, contrastive) pairs, for each
     pressure direction;
  F3 behaviour (reported, not in the outcome): at the pressure direction's break angle, the anchor-bootstrap interval of
     the mean change in expected rating excludes 0 with the sign of the pressure (down for critical, up for praise),
     and its absolute value exceeds the 95th percentile of the randomdiff directions' absolute mean change at that angle.
Outcomes: A = F1 and F2 for both pressure directions (feature-like); B = F1 for both and not F2 (sensitive, not
privileged); C = not F1 for at least one (noise-like). F3 is reported beside the outcome.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SEED = 20261102
B = 10_000
PRESSURE = ("pressure_critical", "pressure_praise")
SIGN = {"pressure_critical": -1.0, "pressure_praise": 1.0}


def ci95(x):
    x = np.asarray(x, float)
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def break_angle(curve, angles, T):
    above = np.nonzero(curve > T)[0]
    return float(angles[above[0]]) if len(above) else float(angles[-1])


def analyse(inp):
    angles = np.asarray(inp["angles_deg"], float)
    dirs = {k: (v["family"], np.asarray(v["l2"], float)) for k, v in inp["directions"].items()}
    fam = lambda f: [k for k, (ff, _) in dirs.items() if ff == f]
    rd = fam("randomdiff")
    if len(rd) < 10 or not all(p in dirs for p in PRESSURE):
        sys.exit("need the two pressure directions and at least 10 randomdiff directions")
    med = lambda k: np.median(dirs[k][1], axis=0)
    T = 0.5 * float(np.median([med(k).max() for k in rd]))
    rd_breaks = np.array([break_angle(med(k), angles, T) for k in rd])
    rd_break_median = float(np.median(rd_breaks))
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(9,)))
    out = {"threshold_T": T, "randomdiff_break_angles": {"median": rd_break_median, "p5": float(np.percentile(rd_breaks, 5)), "n": len(rd)},
           "directions": {}, "pairs": {}, "behaviour": {}, "hypotheses": {}}
    pairs = inp.get("pairs", [])
    cs = set(fam("contrastive"))
    p_of = lambda names: [q["p"] for q in pairs if (q["d1"] in names and q["d2"] in cs) or (q["d2"] in names and q["d1"] in cs)]
    rd_p = np.array(p_of(set(rd)))
    rd_p_ci = ci95([np.median(rng.choice(rd_p, len(rd_p))) for _ in range(B)]) if len(rd_p) else [float("nan")] * 2
    out["pairs"]["randomdiff"] = {"n": int(len(rd_p)), "median_p": (float(np.median(rd_p)) if len(rd_p) else None), "median_p_ci95": rd_p_ci}
    for pd in PRESSURE:
        curves = dirs[pd][1]
        n_anchor = curves.shape[0]
        b = break_angle(np.median(curves, axis=0), angles, T)
        idx = rng.integers(0, n_anchor, size=(B, n_anchor))
        boots = np.array([break_angle(np.median(curves[i], axis=0), angles, T) for i in idx])
        diff_ci = ci95(boots - rd_break_median)
        f1 = bool(diff_ci[1] < 0)
        out["directions"][pd] = {"break_angle_deg": b, "break_angle_ci95": ci95(boots), "minus_randomdiff_median_ci95": diff_ci, "F1": f1}
        pp = np.array(p_of({pd}))
        if len(pp):
            pp_ci = ci95([np.median(rng.choice(pp, len(pp))) for _ in range(B)])
            f2 = bool(len(rd_p) and pp_ci[0] > 2.05 and pp_ci[0] > rd_p_ci[1])
        else:
            pp_ci, f2 = [float("nan")] * 2, None
        out["pairs"][pd] = {"n": int(len(pp)), "median_p": (float(np.median(pp)) if len(pp) else None), "median_p_ci95": pp_ci, "F2": f2}
        beh = inp.get("behaviour", {})
        if pd in beh:
            j = int(np.nonzero(angles == b)[0][0])
            r = np.asarray(beh[pd]["expected_rating"], float)
            delta = r[:, j] - r[:, 0]
            bi = rng.integers(0, len(delta), size=(B, len(delta)))
            d_ci = ci95(delta[bi].mean(1))
            rd_abs = np.array([abs(np.asarray(beh[k]["expected_rating"], float)[:, j].mean() - np.asarray(beh[k]["expected_rating"], float)[:, 0].mean())
                               for k in rd if k in beh])
            thresh = float(np.percentile(rd_abs, 95)) if len(rd_abs) else float("nan")
            signed = (d_ci[0] > 0) if SIGN[pd] > 0 else (d_ci[1] < 0)
            f3 = bool(signed and len(rd_abs) and abs(delta.mean()) > thresh)
            out["behaviour"][pd] = {"angle_deg": b, "mean_change": float(delta.mean()), "mean_change_ci95": d_ci,
                                    "randomdiff_abs_change_p95": thresh, "n_randomdiff": int(len(rd_abs)), "F3": f3}
    h = out["hypotheses"]
    h["F1_sensitive_both"] = bool(all(out["directions"][pd]["F1"] for pd in PRESSURE))
    f2s = [out["pairs"][pd]["F2"] for pd in PRESSURE]
    h["F2_feature_specific_both"] = (bool(all(f2s)) if None not in f2s else None)
    h["F3_behaviour_both"] = (bool(all(out["behaviour"][pd]["F3"] for pd in PRESSURE)) if all(pd in out["behaviour"] for pd in PRESSURE) else None)
    out["outcome"] = outcome(h)
    return out


def outcome(h):
    if not h["F1_sensitive_both"]:
        return "C: at least one pressure direction breaks its plateau no earlier than random difference directions (noise-like)"
    if h["F2_feature_specific_both"]:
        return "A: both pressure directions break early and sit above p = 2 against contrastive partners (feature-like)"
    if h["F2_feature_specific_both"] is None:
        return "F1 holds; F2 not computable (no pairs): reported as such"
    return "B: both pressure directions break early but are not privileged axes (sensitive, not feature-specific)"


def report(res):
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"R9 feature-specific error correction · T = {res['threshold_T']:.3f} · randomdiff break median {res['randomdiff_break_angles']['median']:.1f}° (n = {res['randomdiff_break_angles']['n']})")
    for pd in PRESSURE:
        d, p = res["directions"][pd], res["pairs"][pd]
        line = f"  {pd:<17} break {d['break_angle_deg']:.1f}° {iv(d['break_angle_ci95'])} · minus randomdiff {iv(d['minus_randomdiff_median_ci95'])} · F1={d['F1']}"
        if p["median_p"] is not None:
            line += f" · median p {p['median_p']:.3f} {iv(p['median_p_ci95'])} over {p['n']} pairs · F2={p['F2']}"
        if pd in res["behaviour"]:
            b = res["behaviour"][pd]
            line += f" · rating change at break {b['mean_change']:+.3f} {iv(b['mean_change_ci95'])} (randomdiff p95 {b['randomdiff_abs_change_p95']:.3f}) · F3={b['F3']}"
        print(line)
    rp_ = res["pairs"]["randomdiff"]
    if rp_["median_p"] is not None:
        print(f"  randomdiff pairs: median p {rp_['median_p']:.3f} {iv(rp_['median_p_ci95'])} over {rp_['n']} pairs")
    print("  hypotheses: " + " · ".join(f"{k}={v}" for k, v in res["hypotheses"].items()))
    print(f"  outcome: {res['outcome']}")


def selftest():
    """Synthetic run: the pressure directions break at about 15°, random differences at about 35°; p 2.4 against 2.03;
    the rating moves with the pressure. F1, F2, F3 and outcome A are expected."""
    rng = np.random.default_rng(SEED)
    angles = np.arange(0, 61, 2.0)
    sig = lambda a0, w: 1.0 / (1.0 + np.exp(-(angles - a0) / w))
    curve = lambda a0: np.clip(sig(a0, 4.0)[None, :] * rng.uniform(0.8, 1.2, (30, 1)) + rng.normal(0, 0.02, (30, len(angles))), 0, None)
    dirs = {pd: {"family": pd, "l2": curve(rng.normal(15, 2)).tolist()} for pd in PRESSURE}
    for i in range(40):
        dirs[f"rd{i}"] = {"family": "randomdiff", "l2": curve(rng.normal(35, 4)).tolist()}
    for i in range(12):
        dirs[f"c{i}"] = {"family": "contrastive", "l2": curve(rng.normal(18, 3)).tolist()}
    pairs = []
    for i in range(12):
        for pd in PRESSURE:
            p = rng.normal(2.4, 0.08)
            pairs.append({"d1": pd, "d2": f"c{i}", "p": float(p), "p_ci95": [float(p - 0.1), float(p + 0.1)]})
        for j in range(0, 40, 4):
            p = rng.normal(2.03, 0.05)
            pairs.append({"d1": f"rd{j}", "d2": f"c{i}", "p": float(p), "p_ci95": [float(p - 0.1), float(p + 0.1)]})
    beh = {}
    for name, s in [(PRESSURE[0], -0.6), (PRESSURE[1], 0.6)] + [(f"rd{i}", 0.0) for i in range(40)]:
        base = rng.uniform(1.5, 4.5, 30)
        beh[name] = {"expected_rating": (base[:, None] + s * sig(14, 4.0)[None, :] + rng.normal(0, 0.05, (30, len(angles)))).tolist()}
    res = analyse({"angles_deg": angles.tolist(), "directions": dirs, "pairs": pairs, "behaviour": beh})
    report(res)
    h = res["hypotheses"]
    ok = bool(h["F1_sensitive_both"] and h["F2_feature_specific_both"] and h["F3_behaviour_both"] and res["outcome"].startswith("A"))
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", nargs="?")
    ap.add_argument("--json")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.input:
        ap.error("an input file is required")
    inp = json.loads(Path(args.input).read_text())
    res = analyse(inp)
    res["meta"] = {"run": "R9", "input": args.input, "input_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest()}
    report(res)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
