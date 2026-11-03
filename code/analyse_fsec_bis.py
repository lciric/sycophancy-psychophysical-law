#!/usr/bin/env python3
"""Frozen analysis for R9-bis (preregistrations/2026-11-03_addendum_R9bis_dose_curves.md): the pressure direction under
the error-correction instrument of Ferreira da Silva & Heimersheim (2026, arXiv 2606.24964), read as response curves over
a declared window, against demanding controls and a register-matched neutral direction.

    python3 -I code/analyse_fsec_bis.py INPUT.json [--json OUT]
    python3 -I code/analyse_fsec_bis.py --selftest

It replaces, for R9, the decision rule of code/analyse_fsec.py (archived in v2026.11.5), which is kept unchanged.

INPUT.json (built by the run from the outputs of the FSEC pipeline, github.com/FranciscoHS/fsec-paper; published as
results/R9/R9_fsecbis_input.json, the output as results/R9/R9_fsecbis_output.{json,txt}, run from the repository root):
  layer: 2. The input holds the perturbation layer 2 only; the layer-10 sweeps are reported, not decided.
  angles_deg: the rotation angles of the sweep, exactly 0, 2, ..., 60 degrees.
  directions: {name: {family, l2}} with family in {pressure_critical, pressure_praise, neutral, contrastive, randomdiff,
              random, pca}; l2 is a list of n_anchors lists of len(angles_deg) values (L2 change at the read-out layer,
              FineWeb anchors A, the same anchors in the same order for every direction).
  neutral_for: {pressure_critical: NAME, pressure_praise: NAME}, the neutral direction matched to each pressure sentence
               (the same NAME twice if one neutral sentence matches both).
  pairs: [{d1, d2, p, p_ci95}], the superellipse exponent fitted by the pipeline for every pair with |cos| < 0.1 between a
         direction of family pressure_*, neutral or randomdiff and a contrastive direction.
  behaviour: {name: {expected_rating, digit_mass}} for the pressure, neutral and randomdiff directions: per rating anchor
             (set B, the same anchors for every direction), the expected rating sum_k k p(k) / sum_k p(k) over "1"-"5" at
             each angle, and the mass sum_k p(k) on those tokens (reported by the run, not used here).
Checks: the analysis stops without an outcome if any L2 change or expected rating it uses is not finite, if the behaviour
arrays do not share one shape (n_B anchors x 31), if a (d1, d2) pair appears twice, or if the input is not for layer 2.
A pair whose superellipse fit failed (p null or not finite) is left out of the medians and counted.

Statistics (every interval is a 95 % percentile bootstrap, B = 10 000, seed 20261103, resampling anchors jointly for all
directions, or partner directions for p). Window W = the angles from 2 to 60 degrees, inclusive.
  Anchor-median curve of a direction: at each angle, the median over anchors of its L2 change.
  D(x) = mean over W of [curve of x - median, at each angle, of the randomdiff curves].
  F1-curve, sensitive: for each pressure direction, the interval of D(pressure) lies above 0 and the interval of
     D(pressure) - D(its neutral) lies above 0.
  F2, feature-specific (as in R9): the lower bound of the partner-bootstrap interval of the median p over (pressure,
     contrastive) pairs lies above 2.05 and above the upper bound of the same interval over (randomdiff, contrastive) pairs.
  F3-curve, behaviour (reported, not in the outcome): S(x) = mean over W and over B anchors of the change in expected
     rating from angle 0. For each pressure direction: the interval of S excludes 0 with the sign of the pressure (down for
     critical, up for praise); |S| exceeds the 95th percentile of |S| over the randomdiff directions; and the interval of
     sign x [S(pressure) - S(its neutral)] lies above 0.
  Reported beside them: the randomdiff and contrastive envelopes (median, 2.5 and 97.5 percentiles across directions, at
     each angle); the angles of W where the pressure curve exceeds the randomdiff 97.5 percentile; the mean over W of the
     pressure curve's percentile rank among the contrastive curves; the fraction of randomdiff directions whose D lies
     below D(pressure); and, as the secondary reading kept from R9, the break
     angle (threshold T = 0.5 x the median over randomdiff of their curve maxima) and its difference from the randomdiff
     median break angle.
Outcomes: A = F1-curve and F2 for both pressure directions; B = F1-curve for both and not F2; C = not F1-curve for at
least one. F3-curve is reported beside the outcome.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

SEED = 20261103
B = 10_000
WINDOW = (2.0, 60.0)
PRESSURE = ("pressure_critical", "pressure_praise")
SIGN = {"pressure_critical": -1.0, "pressure_praise": 1.0}


def ci95(x):
    x = np.asarray(x, float)
    return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]


def break_angle(curve, angles, T):
    above = np.nonzero(curve > T)[0]
    return float(angles[above[0]]) if len(above) else float(angles[-1])


def analyse(inp):
    if inp.get("layer") != 2:
        sys.exit("the input holds layer 2 only (layer: 2); the layer-10 sweeps are reported, not decided")
    angles = np.asarray(inp["angles_deg"], float)
    if angles.shape != (31,) or not np.array_equal(angles, np.arange(0, 61, 2.0)):
        sys.exit("angles_deg must be exactly 0, 2, ..., 60 degrees")
    w = (angles >= WINDOW[0]) & (angles <= WINDOW[1])
    dirs = {k: (v["family"], np.asarray(v["l2"], float)) for k, v in inp["directions"].items()}
    fam = lambda f: [k for k, (ff, _) in dirs.items() if ff == f]
    rd, cs = fam("randomdiff"), fam("contrastive")
    nf = inp.get("neutral_for", {})
    if len(rd) < 10 or not all(p in dirs for p in PRESSURE):
        sys.exit("need the two pressure directions and at least 10 randomdiff directions")
    if not all(nf.get(p) in dirs and dirs[nf[p]][0] == "neutral" for p in PRESSURE):
        sys.exit("need a neutral direction for each pressure direction (neutral_for)")
    used = sorted(set(rd) | set(cs) | set(PRESSURE) | {nf[p] for p in PRESSURE})
    n_anchor = dirs[PRESSURE[0]][1].shape[0]
    if any(dirs[k][1].shape != (n_anchor, len(angles)) for k in used):
        sys.exit("every direction needs n_anchors x len(angles_deg) values, on the same anchors")
    if not all(np.isfinite(dirs[k][1]).all() for k in used):
        sys.exit("every L2 change used must be finite")
    pairs = inp.get("pairs", [])
    keys = [tuple(sorted((q["d1"], q["d2"]))) for q in pairs]
    if len(keys) != len(set(keys)):
        sys.exit("a (d1, d2) pair appears more than once")
    rng =np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(11,)))
    idx = rng.integers(0, n_anchor, size=(B, n_anchor))
    med = {k: np.median(dirs[k][1], axis=0) for k in used}                          # point estimates, (A,)
    bmed = {k: np.median(dirs[k][1][idx], axis=1) for k in used}                    # bootstrap, (B, A)
    rd_med, rd_bmed = np.median([med[k] for k in rd], axis=0), np.median([bmed[k] for k in rd], axis=0)
    D = lambda k: float((med[k] - rd_med)[w].mean())
    bD = lambda k: (bmed[k] - rd_bmed)[:, w].mean(axis=1)
    env = lambda names: {"median": np.median([med[k] for k in names], axis=0).tolist(),
                         "p2_5": np.percentile([med[k] for k in names], 2.5, axis=0).tolist(),
                         "p97_5": np.percentile([med[k] for k in names], 97.5, axis=0).tolist()} if names else None
    rd97 = np.percentile([med[k] for k in rd], 97.5, axis=0)
    T = 0.5 * float(np.median([med[k].max() for k in rd]))
    rd_breaks = np.array([break_angle(med[k], angles, T) for k in rd])
    rd_D = np.array([D(k) for k in rd])
    out = {"window_deg": list(WINDOW), "n_window_angles": int(w.sum()), "n_anchors": int(n_anchor),
           "n_randomdiff": len(rd), "n_contrastive": len(cs),
           "envelopes": {"randomdiff": env(rd), "contrastive": env(cs)},
           "secondary_break": {"threshold_T": T, "randomdiff_median_deg": float(np.median(rd_breaks))},
           "directions": {}, "pairs": {}, "behaviour": {}, "hypotheses": {}}
    for pd in PRESSURE:
        nd = nf[pd]
        d_ci, dd_ci = ci95(bD(pd)), ci95(bD(pd) - bD(nd))
        above = [float(a) for a, x, y in zip(angles, med[pd], rd97) if x > y and WINDOW[0] <= a <= WINDOW[1]]
        rank = (float(np.mean([np.mean([med[k][j] < med[pd][j] for k in cs]) for j in np.nonzero(w)[0]])) if cs else None)
        brk = break_angle(med[pd], angles, T)
        out["directions"][pd] = {"neutral": nd, "D": D(pd), "D_ci95": d_ci, "D_neutral": D(nd),
                                 "D_minus_neutral": D(pd) - D(nd), "D_minus_neutral_ci95": dd_ci,
                                 "F1_curve": bool(d_ci[0] > 0 and dd_ci[0] > 0),
                                 "D_rank_among_randomdiff": float(np.mean(rd_D < D(pd))),
                                 "angles_above_randomdiff_p97_5": above, "mean_rank_among_contrastive": rank,
                                 "secondary_break_deg": brk, "secondary_break_minus_randomdiff_median": brk - float(np.median(rd_breaks))}
    def p_of(names):
        v = np.array([np.nan if q["p"] is None else q["p"] for q in pairs
                      if (q["d1"] in names and q["d2"] in cs) or (q["d2"] in names and q["d1"] in cs)], float)
        return v[np.isfinite(v)], int(np.sum(~np.isfinite(v)))
    prng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(12,)))
    med_ci = lambda v: ci95([np.median(prng.choice(v, len(v))) for _ in range(B)]) if len(v) else [float("nan")] * 2
    rd_p, rd_x = p_of(set(rd))
    rd_p_ci = med_ci(rd_p)
    out["pairs"]["randomdiff"] = {"n": int(len(rd_p)), "n_failed_fits_excluded": rd_x,
                                  "median_p": (float(np.median(rd_p)) if len(rd_p) else None), "median_p_ci95": rd_p_ci}
    for name in sorted({nf[p] for p in PRESSURE}):
        v, x = p_of({name})
        out["pairs"][name] = {"n": int(len(v)), "n_failed_fits_excluded": x,
                              "median_p": (float(np.median(v)) if len(v) else None), "median_p_ci95": med_ci(v)}
    for pd in PRESSURE:
        v, x = p_of({pd})
        v_ci = med_ci(v)
        f2 = (bool(len(rd_p) and v_ci[0] > 2.05 and v_ci[0] > rd_p_ci[1]) if len(v) else None)
        out["pairs"][pd] = {"n": int(len(v)), "n_failed_fits_excluded": x,
                            "median_p": (float(np.median(v)) if len(v) else None), "median_p_ci95": v_ci, "F2": f2}
    beh = inp.get("behaviour", {})
    if all(k in beh for k in list(PRESSURE) + [nf[p] for p in PRESSURE]):
        r = {k: np.asarray(v["expected_rating"], float) for k, v in beh.items() if k in used}
        if len({a.shape for a in r.values()}) != 1 or r[PRESSURE[0]].ndim != 2 or r[PRESSURE[0]].shape[1] != len(angles):
            sys.exit("every behaviour array needs n_B anchors x len(angles_deg) values, on the same anchors")
        if not all(np.isfinite(a).all() for a in r.values()):
            sys.exit("every expected rating used must be finite")
        nb = r[PRESSURE[0]].shape[0]
        bidx = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(13,))).integers(0, nb, size=(B, nb))
        S = lambda k: float((r[k] - r[k][:, :1])[:, w].mean())
        bS = lambda k: (r[k] - r[k][:, :1])[:, w][bidx].mean(axis=(1, 2))
        rd_abs = np.array([abs(S(k)) for k in rd if k in r])
        p95 = float(np.percentile(rd_abs, 95)) if len(rd_abs) else float("nan")
        for pd in PRESSURE:
            nd, s = nf[pd], SIGN[pd]
            s_ci, sn_ci = ci95(bS(pd)), ci95(s * (bS(pd) - bS(nd)))
            signed = (s_ci[0] > 0) if s > 0 else (s_ci[1] < 0)
            out["behaviour"][pd] = {"S": S(pd), "S_ci95": s_ci, "S_neutral": S(nd), "signed_minus_neutral_ci95": sn_ci,
                                    "randomdiff_abs_S_p95": p95, "n_randomdiff": int(len(rd_abs)),
                                    "F3_curve": bool(signed and len(rd_abs) and abs(S(pd)) > p95 and sn_ci[0] > 0)}
    h = out["hypotheses"]
    h["F1_curve_both"] = bool(all(out["directions"][pd]["F1_curve"] for pd in PRESSURE))
    f2s = [out["pairs"][pd]["F2"] for pd in PRESSURE]
    h["F2_feature_specific_both"] = (bool(all(f2s)) if None not in f2s else None)
    h["F3_curve_both"] = (bool(all(out["behaviour"][pd]["F3_curve"] for pd in PRESSURE)) if all(pd in out["behaviour"] for pd in PRESSURE) else None)
    out["outcome"] = outcome(h)
    return out


def outcome(h):
    if not h["F1_curve_both"]:
        return "C: over the window, at least one pressure direction does not respond more than random differences and its neutral twin (noise-like)"
    if h["F2_feature_specific_both"]:
        return "A: over the window, both pressure directions respond more than random differences and their neutral twins, and sit above p = 2 against contrastive partners (feature-like)"
    if h["F2_feature_specific_both"] is None:
        return "F1-curve holds; F2 not computable (no pairs): reported as such"
    return "B: over the window, both pressure directions respond more than random differences and their neutral twins, but are not privileged axes (sensitive, not feature-specific)"


def report(res):
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"R9-bis · window {res['window_deg'][0]:.0f}-{res['window_deg'][1]:.0f} deg · {res['n_anchors']} anchors · "
          f"{res['n_randomdiff']} randomdiff · {res['n_contrastive']} contrastive")
    for pd in ("pressure_critical", "pressure_praise"):
        d, p = res["directions"][pd], res["pairs"][pd]
        line = (f"  {pd:<17} D {d['D']:+.4f} {iv(d['D_ci95'])} · minus {d['neutral']} {d['D_minus_neutral']:+.4f} "
                f"{iv(d['D_minus_neutral_ci95'])} · F1-curve={d['F1_curve']} · D above {d['D_rank_among_randomdiff']:.0%} of randomdiff · "
                f"above randomdiff p97.5 at {len(d['angles_above_randomdiff_p97_5'])} angles")
        if p["median_p"] is not None:
            line += f" · median p {p['median_p']:.3f} {iv(p['median_p_ci95'])} over {p['n']} pairs · F2={p['F2']}"
        if pd in res["behaviour"]:
            b = res["behaviour"][pd]
            line += f" · rating change over W {b['S']:+.3f} {iv(b['S_ci95'])} (neutral {b['S_neutral']:+.3f}) · F3-curve={b['F3_curve']}"
        print(line)
    print("  hypotheses: " + " · ".join(f"{k}={v}" for k, v in res["hypotheses"].items()))
    print(f"  outcome: {res['outcome']}")


def synthetic(rng, a_pressure, s_rating, a_neutral=35.0, s_neutral=0.0, p_pressure=2.4, two_neutrals=False,
              twin_identical=False, s_randomdiff=0.0):
    angles = np.arange(0, 61, 2.0)
    sig = lambda a0, wd: 1.0 / (1.0 + np.exp(-(angles - a0) / wd))
    curve = lambda a0: np.clip(sig(a0, 4.0)[None, :] * rng.uniform(0.8, 1.2, (30, 1)) + rng.normal(0, 0.02, (30, len(angles))), 0, None)
    dirs = {pd: {"family": pd, "l2": curve(rng.normal(a_pressure, 1.0)).tolist()} for pd in PRESSURE}
    nf = {PRESSURE[0]: "neutral_c", PRESSURE[1]: "neutral_p"} if two_neutrals else {pd: "neutral_aside" for pd in PRESSURE}
    twin_of = {v: k for k, v in nf.items()}
    for name in sorted(set(nf.values())):
        l2 = dirs[twin_of[name]]["l2"] if twin_identical else curve(rng.normal(a_neutral, 1.0)).tolist()
        dirs[name] = {"family": "neutral", "l2": l2}
    for i in range(40):
        dirs[f"rd{i}"] = {"family": "randomdiff", "l2": curve(rng.normal(35, 4)).tolist()}
    for i in range(12):
        dirs[f"c{i}"] = {"family": "contrastive", "l2": curve(rng.normal(18, 3)).tolist()}
    pairs = []
    for i in range(12):
        for name in list(PRESSURE) + sorted(set(nf.values())):
            pairs.append({"d1": name, "d2": f"c{i}", "p": float(rng.normal(p_pressure if name in PRESSURE else 2.03, 0.06))})
        for j in range(0, 40, 4):
            pairs.append({"d1": f"rd{j}", "d2": f"c{i}", "p": float(rng.normal(2.03, 0.05))})
    shift = {PRESSURE[0]: -s_rating, PRESSURE[1]: s_rating, "neutral_aside": s_neutral, "neutral_c": -s_neutral, "neutral_p": s_neutral}
    beh = {}
    for name in list(PRESSURE) + sorted(set(nf.values())) + [f"rd{i}" for i in range(40)]:
        if twin_identical and name in twin_of:
            beh[name] = beh[twin_of[name]]
            continue
        s = shift.get(name, (s_randomdiff if int(name[2:]) % 2 == 0 else -s_randomdiff) if name.startswith("rd") else 0.0)
        base = rng.uniform(1.5, 4.5, 30)
        beh[name] = {"expected_rating": (base[:, None] + s * sig(14, 4.0)[None, :] + rng.normal(0, 0.05, (30, len(angles)))).tolist()}
    return {"layer": 2, "angles_deg": angles.tolist(), "directions": dirs, "pairs": pairs, "behaviour": beh, "neutral_for": nf}


SELFTEST_CASES = [
    # (name, synthetic arguments, expectation on the result)
    ("sound: pressure responds from 15 deg, neutral and random differences from 35, p 2.4, the rating follows the pressure",
     dict(a_pressure=15.0, s_rating=0.6),
     lambda r: r["n_window_angles"] == 30 and r["hypotheses"]["F1_curve_both"] and r["hypotheses"]["F2_feature_specific_both"]
     and r["hypotheses"]["F3_curve_both"] and r["outcome"].startswith("A")),
    ("faulty: pressure responds like the neutral twin and the random differences, the rating does not move",
     dict(a_pressure=35.0, s_rating=0.0),
     lambda r: (not r["hypotheses"]["F1_curve_both"]) and r["hypotheses"]["F3_curve_both"] is False and r["outcome"].startswith("C")),
    ("faulty twins: two neutral twins respond earlier (12 deg) and move the rating more (0.8) than their pressure direction",
     dict(a_pressure=15.0, s_rating=0.6, a_neutral=12.0, s_neutral=0.8, two_neutrals=True),
     lambda r: r["outcome"].startswith("C") and r["hypotheses"]["F3_curve_both"] is False),
    ("sensitive, not feature-specific: late neutral twin, pressure p about 2.03",
     dict(a_pressure=15.0, s_rating=0.6, p_pressure=2.03),
     lambda r: r["outcome"].startswith("B")),
    ("identical twins: each neutral twin carries exactly its pressure direction's data (joint resampling gives exactly 0)",
     dict(a_pressure=15.0, s_rating=0.6, two_neutrals=True, twin_identical=True),
     lambda r: all(r["directions"][pd]["D_minus_neutral_ci95"] == [0.0, 0.0] and r["behaviour"][pd]["signed_minus_neutral_ci95"] == [0.0, 0.0]
                   for pd in PRESSURE) and r["outcome"].startswith("C") and r["hypotheses"]["F3_curve_both"] is False),
    ("random differences move the rating more than the pressure (1.0 against 0.6)",
     dict(a_pressure=15.0, s_rating=0.6, s_randomdiff=1.0),
     lambda r: r["outcome"].startswith("A") and r["hypotheses"]["F3_curve_both"] is False),
]


def selftest():
    """Six synthetic runs, each with the outcome it must give (SELFTEST_CASES): a sound case (A, with F1-curve, F2 and
    F3-curve), a faulty one (C, no F3-curve), neutral twins that respond earlier and move the rating more than the pressure
    (C, no F3-curve), a pressure direction with p about 2.03 (B), neutral twins identical to the pressure directions (the
    jointly resampled differences are exactly 0: C), and random differences that move the rating more than the pressure
    (A, no F3-curve)."""
    rng = np.random.default_rng(SEED)
    results = []
    for name, kwargs, ok in SELFTEST_CASES:
        res = analyse(synthetic(rng, **kwargs))
        print(f"case: {name}")
        report(res)
        results.append(bool(ok(res)))
    passed = all(results)
    print("SELFTEST PASSED" if passed else f"SELFTEST FAILED (cases as expected: {results})")
    return 0 if passed else 1


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
    res["meta"] = {"run": "R9-bis", "input": args.input, "input_sha256": hashlib.sha256(Path(args.input).read_bytes()).hexdigest()}
    report(res)
    if args.json:
        Path(args.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
