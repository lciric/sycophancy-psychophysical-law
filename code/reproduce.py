#!/usr/bin/env python3
"""Recompute every number quoted in README.md from the files in data/.

    python3 -I code/reproduce.py                    # print the report
    python3 -I code/reproduce.py --check            # also compare with code/expected.json; exit 1 on any drift
    python3 -I code/reproduce.py --write-expected   # maintainers only: rewrite code/expected.json

Only numpy is needed (pinned in requirements.txt). Each random procedure draws from
its own named child of SeedSequence(20261101), so every resampled number is exact
for the pinned numpy and reproducible on its own.

Notation, per item of an arm: p0 = mean judged rating (1-5 scale) over the K
generations without pressure, p1 = the same with the pressure suffix, D = p1 - p0.
The law D = g (c - p0) is fitted by ordinary least squares of p1 on p0, i.e.
p1 = (1 - g) p0 + g c. "R2" is the coefficient of determination of D under the law.
Before computing anything, the script checks the custody chain and aborts on any break.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
EXPECTED = ROOT / "code" / "expected.json"
SEED = 20261101
B_BOOT, B_PERM, B_ARM = 10_000, 40_000, 10_000
STREAMS = ["boot_critical", "boot_praise", "boot_joint", "perm_critical", "perm_praise", "perm_arms",
           "boot_campaign2", "perm_campaign2_critical", "perm_campaign2_praise"]
ARMS = {"critical": ("c2a", "pre", "crit"), "praise": ("c2b", "praise", "elo")}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(msg):
    sys.exit(f"INTEGRITY FAILURE: {msg}")


def ols(p0, p1):
    """Least-squares fit of p1 = (1 - g) p0 + g c along the last axis; returns (g, c)."""
    x, y = p0 - p0.mean(-1, keepdims=True), p1 - p1.mean(-1, keepdims=True)
    slope = (x * y).sum(-1) / (x * x).sum(-1)
    intercept = p1.mean(-1) - slope * p0.mean(-1)
    g = 1.0 - slope
    with np.errstate(divide="ignore", invalid="ignore"):
        return g, intercept / g


def r2(d, pred):
    return float(1.0 - ((d - pred) ** 2).sum() / ((d - d.mean()) ** 2).sum())


def loo_r2(p0, p1):
    n, pred = len(p0), np.empty(len(p0))
    for i in range(n):
        keep = np.arange(n) != i
        g, c = ols(p0[keep], p1[keep])
        pred[i] = g * (c - p0[i])
    return r2(p1 - p0, pred)


def ci95(x):
    lo, hi = np.percentile(x, [2.5, 97.5])
    return [float(lo), float(hi)]


def p_at_least(null, observed):
    """One-sided resampling p-value with the +1 correction; its floor is 1/(B+1)."""
    return float((1 + np.count_nonzero(null >= observed - 1e-12)) / (len(null) + 1))


def p_at_most(null, observed):
    return float((1 + np.count_nonzero(null <= observed + 1e-12)) / (len(null) + 1))


def toward(d, c, p0):
    """Mobile items whose displacement has the sign of (c - p0)."""
    mobile = np.abs(d) > 1e-9
    return mobile & (np.sign(d) == np.sign(c - p0)), mobile


def load_campaign1(arm):
    stem, key, _ = ARMS[arm]
    res_path, gen_path = DATA / f"{stem}_results.json", DATA / f"{stem}_generations.json"
    res, gen = json.loads(res_path.read_text()), json.loads(gen_path.read_text())
    table = res["table"]
    ids = sorted(table, key=int)
    neu = np.array([table[i]["pol_neu"] for i in ids], dtype=float)
    pre = np.array([table[i][f"pol_{key}"] for i in ids], dtype=float)
    stored = np.array([[table[i]["mean_neu"], table[i][f"mean_{key}"]] for i in ids])

    if not np.allclose(stored, np.c_[neu.mean(1), pre.mean(1)], atol=1e-9):
        fail(f"{res_path.name}: stored item means differ from the means of the per-generation ratings")
    if res["meta"]["gen_sha"] != sha256(gen_path):
        fail(f"{res_path.name}: meta.gen_sha does not match the SHA-256 of {gen_path.name}")
    rows = gen["rows"]
    base = int(re.match(r"(\d+)\+100\*i\+k", gen["meta"]["seeds"]).group(1))
    if len(rows) != len(ids) * neu.shape[1] * 2 or len({(r["item"], r["k"], r["cond"]) for r in rows}) != len(rows):
        fail(f"{gen_path.name}: expected exactly one generation per item, seed index and condition")
    if any(int(r["seed"]) != base + 100 * int(r["item"]) + int(r["k"]) for r in rows):
        fail(f"{gen_path.name}: a seed departs from the declared formula {gen['meta']['seeds']}")

    seeds = {}
    for r in rows:
        seeds.setdefault(r["item"], set()).add(int(r["seed"]))
    custody = {"results_sha256": sha256(res_path), "generations_sha256": sha256(gen_path),
               "generations": len(rows), "seed_formula": gen["meta"]["seeds"],
               "model": gen["meta"]["model"], "generation_settings": gen["meta"]["gen_kwargs"],
               "pressure_suffix": gen["meta"].get("press") or gen["meta"].get("praise"),
               "judge": res["meta"]["judge"], "judge_prompt_sha256": res["meta"]["prompt_sha"],
               "preregistration_sha256": res["meta"]["prereg_sha"]}
    return neu, pre, seeds, custody


def permutation_null(neu, pre, rng, fixed_target=None):
    """Intra-item permutation: under 'the pressure has no effect' the 2K ratings of an item are
    exchangeable between the two labels; nothing moves between items. Unless a target is fixed
    from another campaign, g and c are re-estimated in every replicate."""
    n, k = neu.shape
    ratings = np.concatenate([neu, pre], axis=1)
    keys = ["g", "concordant", "mobile", "descending_above", "mean_d_above", "nonfinite_target"]
    acc = {key: [] for key in keys}
    for start in range(0, B_PERM, 5_000):
        arr = np.broadcast_to(ratings, (min(5_000, B_PERM - start), n, 2 * k)).copy()
        rng.permuted(arr, axis=2, out=arr)
        p0, p1 = arr[..., :k].mean(-1), arr[..., k:].mean(-1)
        g, c = ols(p0, p1)
        if fixed_target is not None:
            c = np.full(len(g), fixed_target)
        d = p1 - p0
        conc, mobile = toward(d, c[:, None], p0)
        above = p0 > c[:, None]
        n_above = above.sum(1)
        acc["g"].append(g)
        acc["concordant"].append(conc.sum(1))
        acc["mobile"].append(mobile.sum(1))
        acc["descending_above"].append((above & (d < 0)).sum(1))
        acc["mean_d_above"].append(np.where(n_above > 0, (d * above).sum(1) / np.maximum(n_above, 1), 0.0))
        acc["nonfinite_target"].append(~np.isfinite(c))
    return {key: np.concatenate(v) for key, v in acc.items()}


def sign_block(conc, mobile, null):
    prop0 = np.where(null["mobile"] > 0, null["concordant"] / np.maximum(null["mobile"], 1), 0.0)
    return {"concordant": int(conc.sum()), "mobile": int(mobile.sum()),
            "replicates_count_at_least_observed": int(np.count_nonzero(null["concordant"] >= conc.sum())),
            "p_count": p_at_least(null["concordant"], conc.sum()),
            "p_proportion": p_at_least(prop0, conc.sum() / mobile.sum()),
            "null_median_proportion": float(np.median(prop0)), "null_median_mobile": float(np.median(null["mobile"])),
            "null_replicates_with_infinite_target": int(null["nonfinite_target"].sum())}


def shared_gain(x0, x1, y0, y1):
    """One gain for both arms, one target per arm (within-arm demeaned least squares of D on p0)."""
    cx, cy = x0 - x0.mean(-1, keepdims=True), y0 - y0.mean(-1, keepdims=True)
    dx, dy = x1 - x0, y1 - y0
    num = ((dx - dx.mean(-1, keepdims=True)) * cx).sum(-1) + ((dy - dy.mean(-1, keepdims=True)) * cy).sum(-1)
    g = -num / ((cx * cx).sum(-1) + (cy * cy).sum(-1))
    return g, (dx.mean(-1) + g * x0.mean(-1)) / g, (dy.mean(-1) + g * y0.mean(-1)) / g


def analyse():
    children = np.random.SeedSequence(SEED).spawn(len(STREAMS))
    rng = {name: np.random.default_rng(child) for name, child in zip(STREAMS, children)}
    out = {"seed": SEED, "B_bootstrap": B_BOOT, "B_permutation": B_PERM, "B_arm_swap": B_ARM, "numpy": np.__version__,
           "campaign1": {}, "rivals": {}, "campaign2": {}}
    p0s, p1s, fits, seeds = {}, {}, {}, {}

    # Campaign 1: the law per arm, item-bootstrap intervals, and the no-effect rival
    for arm in ARMS:
        neu, pre, seeds[arm], custody = load_campaign1(arm)
        p0, p1 = neu.mean(1), pre.mean(1)
        d = p1 - p0
        p0s[arm], p1s[arm] = p0, p1
        g, c = ols(p0, p1)
        fits[arm] = (float(g), float(c))
        idx = rng[f"boot_{arm}"].integers(0, len(p0), size=(B_BOOT, len(p0)))
        gb, cb = ols(p0[idx], p1[idx])
        null = permutation_null(neu, pre, rng[f"perm_{arm}"])
        conc, mobile = toward(d, c, p0)
        out["campaign1"][arm] = {
            "items": len(p0), "K": neu.shape[1], "g": float(g), "g_ci95": ci95(gb), "c": float(c), "c_ci95": ci95(cb),
            "R2": r2(d, g * (c - p0)), "LOO_R2": loo_r2(p0, p1), "mean_p0": float(p0.mean()),
            "mean_displacement": float(d.mean()), "custody": custody}
        out["rivals"][f"no_effect_slope_{arm}"] = {
            "g": float(g), "null_median_g": float(np.median(null["g"])), "p": p_at_least(null["g"], g)}
        out["rivals"][f"no_effect_sign_{arm}"] = sign_block(conc, mobile, null)

        if arm == "praise":
            above = p0 > c
            upper = out["campaign1"][arm]["c_ci95"][1]
            halves = []
            for sel, mea in [(slice(0, 5), slice(5, 10)), (slice(5, 10), slice(0, 5))]:
                chosen = neu[:, sel].mean(1) > c
                dm = pre[:, mea].mean(1) - neu[:, mea].mean(1)
                halves.append({"selected": int(chosen.sum()), "descending": int((chosen & (dm < 0)).sum()),
                               "mean_displacement": float(dm[chosen].mean())})
            out["rivals"]["directional_push"] = {
                "items_above_target": int(above.sum()), "descending": int((above & (d < 0)).sum()),
                "mean_displacement_above_target": float(d[above].mean()),
                "null_median_mean_displacement": float(np.median(null["mean_d_above"])),
                "p_mean_displacement": p_at_most(null["mean_d_above"], d[above].mean()),
                "null_median_descending": float(np.median(null["descending_above"])),
                "p_descending_count": p_at_least(null["descending_above"], (above & (d < 0)).sum()),
                "items_above_target_upper_ci": int((p0 > upper).sum()),
                "descending_above_upper_ci": int(((p0 > upper) & (d < 0)).sum()), "target_upper_ci": upper,
                "selection_free_halves": halves}

    # One destination: are the two targets separated beyond an exchange of arm labels?
    a0, a1, b0, b1 = p0s["critical"], p1s["critical"], p0s["praise"], p1s["praise"]
    gap = fits["praise"][1] - fits["critical"][1]
    swap = rng["perm_arms"].random((B_ARM, len(a0))) < 0.5
    _, ca = ols(np.where(swap, b0, a0), np.where(swap, b1, a1))
    _, cb = ols(np.where(swap, a0, b0), np.where(swap, a1, b1))
    null_gap = np.abs(cb - ca)
    null_gap = np.where(np.isfinite(null_gap), null_gap, np.inf)
    out["rivals"]["one_destination"] = {
        "gap": float(gap), "mean_p0_critical_campaign": float(a0.mean()), "mean_p0_praise_campaign": float(b0.mean()),
        "replicates_at_least_observed": int(np.count_nonzero(null_gap >= abs(gap))),
        "p": p_at_least(null_gap, abs(gap)), "null_max_gap": float(null_gap[np.isfinite(null_gap)].max())}

    # Shared gain and the equality of gains (items resampled jointly: same items in both arms)
    gs, cs_a, cs_b = shared_gain(a0, a1, b0, b1)
    idx = rng["boot_joint"].integers(0, len(a0), size=(B_BOOT, len(a0)))
    gsb, _, _ = shared_gain(a0[idx], a1[idx], b0[idx], b1[idx])
    diff = ols(a0[idx], a1[idx])[0] - ols(b0[idx], b1[idx])[0]
    out["campaign1"]["shared_gain"] = {"g": float(gs), "g_ci95": ci95(gsb), "c_critical": float(cs_a), "c_praise": float(cs_b)}
    out["campaign1"]["gain_difference"] = {
        "critical_minus_praise": fits["critical"][0] - fits["praise"][0], "ci95": ci95(diff),
        "p_two_sided": float(min(1.0, 2 * min(np.mean(diff <= 0), np.mean(diff >= 0))))}
    praise_sets = list(seeds["praise"].values())
    out["campaign1"]["items_whose_seed_set_recurs_in_the_other_campaign"] = sum(s in praise_sets for s in seeds["critical"].values())

    # Campaign 2: refit per prefix stratum, and the campaign-1 law applied with no free parameter
    c2_path = DATA / "c2full_polarity_2026-08-02.json"
    c2 = json.loads(c2_path.read_text())
    pol, meta = c2["pol"], c2["meta"]
    items = sorted({key.split("|")[0] for key in pol}, key=int)
    k2 = len(pol[f"{items[0]}|S0|neu"])
    if len(pol) != len(items) * 9 or any(len(v) != k2 for v in pol.values()):
        fail(f"{c2_path.name}: expected {len(items)} items x 3 strata x 3 conditions with {k2} ratings each")
    neu2 = np.array([pol[f"{i}|S0|neu"] for i in items], dtype=float)
    out["campaign2"] = {
        "file_sha256": sha256(c2_path), "items": len(items), "K": k2, "generations_file": meta["generations_file"],
        "generations_sha256": meta["generations_sha256"], "judge": meta["judge_model"],
        "judge_prompt_sha256": meta["prompt_sha"], "predictions_sha256": meta["pred_sha"],
        "r_unpressured_means_ids_0_29_vs_campaign1": [float(np.corrcoef(neu2[:30].mean(1), a0)[0, 1]),
                                                     float(np.corrcoef(neu2[:30].mean(1), b0)[0, 1])],
        "strata": {}, "out_of_sample": {}}
    for stratum in ["S0", "Sp", "Sm"]:
        p0 = np.array([np.mean(pol[f"{i}|{stratum}|neu"]) for i in items])
        for arm, (_, _, cond) in ARMS.items():
            p1 = np.array([np.mean(pol[f"{i}|{stratum}|{cond}"]) for i in items])
            g, c = ols(p0, p1)
            idx = rng["boot_campaign2"].integers(0, len(p0), size=(B_BOOT, len(p0)))
            gb, cb = ols(p0[idx], p1[idx])
            out["campaign2"]["strata"][f"{stratum}_{arm}"] = {
                "g": float(g), "g_ci95": ci95(gb), "c": float(c), "c_ci95": ci95(cb), "R2": r2(p1 - p0, g * (c - p0))}
    for arm, (_, _, cond) in ARMS.items():
        pre2 = np.array([pol[f"{i}|S0|{cond}"] for i in items], dtype=float)
        p0, p1 = neu2.mean(1), pre2.mean(1)
        d = p1 - p0
        g1, c1 = fits[arm]
        pred = g1 * (c1 - p0)
        new = np.array([int(i) >= 30 for i in items])
        conc, mobile = toward(d, c1, p0)
        null = permutation_null(neu2, pre2, rng[f"perm_campaign2_{arm}"], fixed_target=c1)
        out["campaign2"]["out_of_sample"][arm] = {
            "R2_all_items": r2(d, pred), "R2_refit": out["campaign2"]["strata"][f"S0_{arm}"]["R2"],
            "R2_new_items": r2(d[new], pred[new]), "new_items": int(new.sum()),
            "toward_campaign1_target": sign_block(conc, mobile, null)}
    return out


def report(o):
    c1, rv, c2 = o["campaign1"], o["rivals"], o["campaign2"]
    f = lambda x: f"{x:.3f}"
    iv = lambda v: f"[{v[0]:.3f}, {v[1]:.3f}]"
    print(f"numpy {o['numpy']} · seed {o['seed']} · bootstrap B = {o['B_bootstrap']} · permutation B = {o['B_permutation']} · arm swap B = {o['B_arm_swap']}")
    print("custody checks passed: item means = means of per-generation ratings; meta.gen_sha = SHA-256 of generation file; seeds follow the declared formulas\n")
    print("CAMPAIGN 1 — Llama-3.1-8B-Instruct, 30 items x K = 10 generations per condition and arm")
    print(f"{'arm':<9}{'g':>7}  {'95% CI':<17}{'c':>7}  {'95% CI':<17}{'R2':>6}{'LOO R2':>8}{'mean D':>8}")
    for arm in ARMS:
        a = c1[arm]
        print(f"{arm:<9}{f(a['g']):>7}  {iv(a['g_ci95']):<17}{f(a['c']):>7}  {iv(a['c_ci95']):<17}{f(a['R2']):>6}{f(a['LOO_R2']):>8}{a['mean_displacement']:>+8.3f}")
    sg, gd = c1["shared_gain"], c1["gain_difference"]
    print(f"shared gain g = {f(sg['g'])} {iv(sg['g_ci95'])}; targets {f(sg['c_critical'])} / {f(sg['c_praise'])}")
    print(f"g_critical - g_praise = {gd['critical_minus_praise']:+.3f} {iv(gd['ci95'])}, bootstrap p = {gd['p_two_sided']:.2f}  -> equality not established")
    print(f"items whose ten seeds recur, attached to another item, in the other campaign: {c1['items_whose_seed_set_recurs_in_the_other_campaign']}/30\n")
    print("RIVAL 1 — no effect (noise and regression to the mean); intra-item permutation, g and c re-estimated")
    for arm in ARMS:
        s, x = rv[f"no_effect_slope_{arm}"], rv[f"no_effect_sign_{arm}"]
        print(f"  {arm:<9}g = {f(s['g'])} vs null median {f(s['null_median_g'])}, p = {s['p']:.1e} · toward c: {x['concordant']}/{x['mobile']} mobile, "
              f"null median proportion {x['null_median_proportion']:.3f}, p = {x['p_proportion']:.1e} (proportion) / {x['p_count']:.1e} (count, "
              f"{x['replicates_count_at_least_observed']}/{o['B_permutation']}); infinite refitted targets in null: {x['null_replicates_with_infinite_target']}")
    t = rv["one_destination"]
    print(f"RIVAL 2 — one destination: targets {f(t['gap'])} apart on either side of unpressured corpus means {f(t['mean_p0_critical_campaign'])} / "
          f"{f(t['mean_p0_praise_campaign'])}; {t['replicates_at_least_observed']}/{o['B_arm_swap']} arm-label swaps reach it (p = {t['p']:.1e}; null max {f(t['null_max_gap'])})")
    x = rv["directional_push"]
    h = x["selection_free_halves"]
    print(f"RIVAL 3 — directional push: {x['items_above_target']} praise items above c move by {x['mean_displacement_above_target']:+.3f} under praise "
          f"({x['descending']} descend); no-effect null median {x['null_median_mean_displacement']:+.3f}, p = {x['p_mean_displacement']:.1e}")
    print(f"  count of descents alone: null median {x['null_median_descending']:.0f}, p = {x['p_descending_count']:.2f}  -> the count does not discriminate, the magnitude does")
    print(f"  above the CI upper bound {f(x['target_upper_ci'])}: {x['descending_above_upper_ci']}/{x['items_above_target_upper_ci']} descend")
    print(f"  selection-free halves (select on 5 unpressured generations, measure on the other 5): "
          + " ; ".join(f"{v['descending']}/{v['selected']} descend, mean {v['mean_displacement']:+.3f}" for v in h) + "\n")
    print(f"CAMPAIGN 2 — {c2['items']} items (ids 0-29 + 10 new) x K = {c2['K']}, three prefix strata; "
          f"r(unpressured means, ids 0-29 vs campaign 1) = {c2['r_unpressured_means_ids_0_29_vs_campaign1'][0]:.3f} / {c2['r_unpressured_means_ids_0_29_vs_campaign1'][1]:.3f}")
    print(f"{'cell':<13}{'g':>7}  {'95% CI':<17}{'c':>7}  {'95% CI':<17}{'R2':>6}")
    for key, v in c2["strata"].items():
        print(f"{key:<13}{f(v['g']):>7}  {iv(v['g_ci95']):<17}{f(v['c']):>7}  {iv(v['c_ci95']):<17}{f(v['R2']):>6}")
    print("campaign-1 law applied to S0 with no free parameter:")
    for arm, v in c2["out_of_sample"].items():
        x = v["toward_campaign1_target"]
        print(f"  {arm:<9}R2 = {f(v['R2_all_items'])} (refit {f(v['R2_refit'])}) · {v['new_items']} new items alone R2 = {f(v['R2_new_items'])} · "
              f"toward the campaign-1 target {x['concordant']}/{x['mobile']}, null median {x['null_median_proportion']:.3f}, p = {x['p_proportion']:.1e}")


def compare(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        keys = sorted(set(a) | set(b))
        return [m for k in keys for m in (compare(a[k], b[k], f"{path}.{k}") if k in a and k in b else [f"{path}.{k}: missing"])]
    if isinstance(a, list) and isinstance(b, list):
        return ([f"{path}: length {len(a)} != {len(b)}"] if len(a) != len(b) else []) + [m for i, (x, y) in enumerate(zip(a, b)) for m in compare(x, y, f"{path}[{i}]")]
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return [] if abs(a - b) <= 1e-9 * max(1.0, abs(b)) else [f"{path}: {a!r} != expected {b!r}"]
    return [] if a == b else [f"{path}: {a!r} != expected {b!r}"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write-expected", action="store_true")
    args = ap.parse_args()
    out = analyse()
    report(out)
    if args.write_expected:
        EXPECTED.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
        print(f"\nwrote {EXPECTED.relative_to(ROOT)}")
    if args.check:
        drift = compare(out, json.loads(EXPECTED.read_text()))
        print("\nCHECK PASSED: every number matches code/expected.json" if not drift else "\nCHECK FAILED:\n  " + "\n  ".join(drift))
        return 1 if drift else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
