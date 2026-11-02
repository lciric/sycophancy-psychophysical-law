#!/usr/bin/env python3
"""Frozen analysis for the preregistered run R5: human readers of the released responses.

    python3 -I code/analyse_humans.py RATINGS.csv [--json OUT]
    python3 -I code/analyse_humans.py --selftest

RATINGS.csv has one row per rating with the columns participant_id, id, rating (an integer 1-5), where id is a
stimulus id of preregistrations/R5_materials/R5_stimuli.csv (R000-R239, ATT_NEG, ATT_POS). It is the Prolific export
reduced to these three columns; nothing else is used.

Exclusion (fixed in section 3 R5 before any data): a reader who fails either attention check is excluded, with all
their ratings. ATT_NEG passes at 1 or 2, ATT_POS at 4 or 5; a reader who did not rate both checks is excluded. A reader
who took several sessions met each check once per session: every one of those ratings must pass. A reader who rated the
same response twice stops the analysis (the session plan forbids it).

Analysis: per response, the mean over its valid readers. Per item, arm and condition, the two responses k = 0, 1 give
K = 2 values, analysed by code/analyse_runs.py (C1, C2, regime). C5: per arm, Spearman's rho between the human item
displacements and the campaign-1 judge's item displacements on the same responses (k = 0, 1, from data/), with a 95 %
item-bootstrap percentile interval (B = 10 000, seed 20261105); C5 holds if the interval excludes 0 in both arms.
Outcome A: C1, C2 and C5 hold. Outcome B: any fails.
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
spec = importlib.util.spec_from_file_location("analyse_runs", HERE / "analyse_runs.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
rp = ar.rp

SEED = 20261105
STIMULI = ROOT / "preregistrations" / "R5_materials" / "R5_stimuli.csv"
VALID = {"ATT_NEG": {1, 2}, "ATT_POS": {4, 5}}
JUDGE = {"critical": ("data/c2a_results.json", "pol_pre"), "praise": ("data/c2b_results.json", "pol_praise")}


def ranks(x):
    """Average ranks along the last axis (ties share their mean rank)."""
    x = np.asarray(x, dtype=float)
    order = np.argsort(x, axis=-1, kind="stable")
    r = np.empty_like(x)
    np.put_along_axis(r, order, np.arange(x.shape[-1], dtype=float) + 1, axis=-1)
    flat_x, flat_r = x.reshape(-1, x.shape[-1]), r.reshape(-1, x.shape[-1])
    for row_x, row_r in zip(flat_x, flat_r):
        vals, inv, cnt = np.unique(row_x, return_inverse=True, return_counts=True)
        if (cnt > 1).any():
            sums = np.bincount(inv, weights=row_r)
            row_r[:] = (sums / cnt)[inv]
    return flat_r.reshape(x.shape)


def spearman(a, b):
    ra, rb = ranks(a), ranks(b)
    ra = ra - ra.mean(-1, keepdims=True)
    rb = rb - rb.mean(-1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (ra * rb).sum(-1) / np.sqrt((ra * ra).sum(-1) * (rb * rb).sum(-1))


def load_stimuli():
    rows = list(csv.DictReader(STIMULI.open()))
    return {r["id"]: r for r in rows}


def load_ratings(path, stim):
    by_reader = {}
    for r in csv.DictReader(Path(path).open()):
        sid, rating = r["id"].strip(), int(r["rating"])
        if sid not in stim or not 1 <= rating <= 5:
            rp.fail(f"bad rating row: {r}")
        by_reader.setdefault(r["participant_id"].strip(), []).append((sid, rating))
    return by_reader


def analyse(ratings_path, label="R5"):
    stim = load_stimuli()
    by_reader = load_ratings(ratings_path, stim)
    valid, excluded = {}, []
    for pid, rs in sorted(by_reader.items()):
        seen = [sid for sid, _ in rs if sid not in VALID]
        if len(seen) != len(set(seen)):
            rp.fail(f"reader {pid} rated the same response twice")
        checks = {}
        for sid, rating in rs:
            if sid in VALID:
                checks.setdefault(sid, []).append(rating)
        ok = all(sid in checks and all(r in VALID[sid] for r in checks[sid]) for sid in VALID)
        (valid.__setitem__(pid, rs) if ok else excluded.append(pid))
    per_resp = {}
    for pid, rs in valid.items():
        for sid, rating in rs:
            if sid not in VALID:
                per_resp.setdefault(sid, []).append(rating)
    missing = [sid for sid in stim if sid not in VALID and sid not in per_resp]
    if missing:
        rp.fail(f"{len(missing)} responses have no valid reader (e.g. {missing[:3]}): recruit replacements before analysis")
    arms = {"critical": {}, "praise": {}}
    human = {}
    for sid, s in stim.items():
        if sid in VALID:
            continue
        key = (s["META_arm"], int(s["META_item"]), s["META_condition"], int(s["META_k"]))
        human[key] = float(np.mean(per_resp[sid]))
    for arm in arms:
        for i in range(30):
            arms[arm][str(i)] = {c: [human[(arm, i, c, k)] for k in (0, 1)] for c in ("neutral", "pressure")}
    tmp = HERE / ".r5_input.json"
    tmp.write_text(json.dumps({"meta": {"run": label}, "arms": arms}))
    _, items, data = ar.load(tmp)
    tmp.unlink()
    res = ar.analyse(data)

    rng = np.random.default_rng(np.random.SeedSequence(SEED))
    c5 = {}
    idx = rng.integers(0, 30, size=(rp.B_BOOT, 30))
    for arm, (rel, key) in JUDGE.items():
        table = json.loads((ROOT / rel).read_text())["table"]
        dj = np.array([np.mean(table[str(i)][key][:2]) - np.mean(table[str(i)]["pol_neu"][:2]) for i in range(30)])
        dh = np.array([np.mean(arms[arm][str(i)]["pressure"]) - np.mean(arms[arm][str(i)]["neutral"]) for i in range(30)])
        rho = float(spearman(dh, dj))
        boot = spearman(dh[idx], dj[idx])
        boot = boot[np.isfinite(boot)]
        c5[arm] = {"rho": rho, "rho_ci95": rp.ci95(boot), "replicates_dropped": int(rp.B_BOOT - len(boot))}
    c5_ok = all(c5[a]["rho_ci95"][0] > 0 or c5[a]["rho_ci95"][1] < 0 for a in c5)
    crit = dict(res["criteria"], C5_humans_track_judge=bool(c5_ok))
    outcome = "A" if all(crit.values()) else "B"
    readers = [len(v) for v in per_resp.values()]
    return {"run": label, "readers_total": len(by_reader), "readers_excluded": len(excluded), "excluded_ids": excluded,
            "valid_readers_per_response": {"min": int(min(readers)), "median": float(np.median(readers)), "max": int(max(readers))},
            "analysis": res, "C5": c5, "criteria": crit, "outcome": outcome}


def report(out):
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"{out['run']} human readers · {out['readers_total']} readers, {out['readers_excluded']} excluded by attention checks · valid readers per response "
          f"min {out['valid_readers_per_response']['min']}, median {out['valid_readers_per_response']['median']}")
    for arm, a in out["analysis"]["arms"].items():
        print(f"  {arm:<9} g={a['g']:.3f} {iv(a['g_ci95'])} c={a['c']:.3f} {iv(a['c_ci95'])} mean D={a['mean_displacement']:+.3f} · "
              f"rho(human, judge)={out['C5'][arm]['rho']:.3f} {iv(out['C5'][arm]['rho_ci95'])}")
    print("  criteria: " + " · ".join(f"{k}={v}" for k, v in out["criteria"].items()) + f" · outcome {out['outcome']}")


def selftest():
    """Simulated readers who read the campaign-1 judge ratings with noise, plus two careless readers: outcome A expected,
    the two careless readers excluded."""
    rng = np.random.default_rng(SEED)
    stim = load_stimuli()
    judge = {}
    for arm, (rel, key) in JUDGE.items():
        table = json.loads((ROOT / rel).read_text())["table"]
        for i in range(30):
            for k in (0, 1):
                judge[(arm, i, "neutral", k)] = table[str(i)]["pol_neu"][k]
                judge[(arm, i, "pressure", k)] = table[str(i)][key][k]
    groups = {}
    for g in csv.DictReader((STIMULI.parent / "R5_groups.csv").open()):
        groups.setdefault(g["META_TASK_GROUP_ID"], []).append(g["id"])
    rows = []
    for p, gid in enumerate(sorted(groups) + ["G00", "G01"]):  # 30 careful readers, one group each; then 2 careless readers
        careless = p >= 30
        for sid in groups[gid]:
            s = stim[sid]
            if sid in VALID:
                r = 3 if careless else (1 if sid == "ATT_NEG" else 5)
            elif careless:
                r = int(rng.integers(1, 6))
            else:
                key = (s["META_arm"], int(s["META_item"]), s["META_condition"], int(s["META_k"]))
                r = int(np.clip(np.rint(judge[key] + rng.normal(0, 0.7)), 1, 5))
            rows.append({"participant_id": f"P{p:02d}", "id": sid, "rating": r})
    path = HERE / ".r5_selftest.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["participant_id", "id", "rating"])
        w.writeheader()
        w.writerows(rows)
    rp.B_PERM = 2_000
    try:
        out = analyse(path)
    finally:
        path.unlink()
    report(out)
    ok = out["readers_excluded"] == 2 and out["criteria"]["C5_humans_track_judge"] and out["criteria"]["C1_attraction"]
    print("SELFTEST PASSED" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ratings", nargs="?")
    ap.add_argument("--json")
    ap.add_argument("--label", default="R5", help="R5 (Prolific, as preregistered) or R5-pilot (acquaintance readers, declared note)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.ratings:
        ap.error("a ratings file is required")
    out = analyse(args.ratings, label=args.label)
    report(out)
    if args.json:
        Path(args.json).write_text(json.dumps(out, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
