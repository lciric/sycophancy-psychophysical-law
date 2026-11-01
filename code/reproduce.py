#!/usr/bin/env python3
"""Recompute the attraction-law figures from the deposited result files.

Usage (from the repository root):  python3 -I code/reproduce.py

Model under study: Llama-3.1-8B-Instruct. Judge: claude-opus-4-6 (t = 0),
ordinal polarity prompt sha256 6c95c1c0… (recorded in each file's `meta`).
Law: Delta = g * (c - p0), fitted by ordinary least squares on item means
(p1 = (1 - g) p0 + g c). R^2 is the coefficient of determination of the
displacement Delta. "LOO R^2" refits the law with each item left out in turn
and scores the held-out displacement (leave-one-item-out cross-validation).
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def fit(p0, p1):
    A = np.c_[p0, np.ones_like(p0)]
    (a, b), *_ = np.linalg.lstsq(A, p1, rcond=None)
    g, c = 1.0 - a, b / (1.0 - a)
    delta, pred = p1 - p0, A @ [a, b] - p0
    r2 = 1.0 - ((delta - pred) ** 2).sum() / ((delta - delta.mean()) ** 2).sum()
    return g, c, r2


def loo_r2(p0, p1):
    n, pred = len(p0), np.empty(len(p0))
    for i in range(n):
        m = np.arange(n) != i
        A = np.c_[p0[m], np.ones(m.sum())]
        (a, b), *_ = np.linalg.lstsq(A, p1[m], rcond=None)
        pred[i] = a * p0[i] + b - p0[i]
    delta = p1 - p0
    return 1.0 - ((delta - pred) ** 2).sum() / ((delta - delta.mean()) ** 2).sum()


def campaign1(path, key):
    t = json.load(open(path))["table"]
    ids = sorted(t, key=int)
    p0 = np.array([t[i]["mean_neu"] for i in ids])
    p1 = np.array([t[i][key] for i in ids])
    k = {len(t[i]["pol_neu"]) for i in ids} | {len(t[i][key.replace("mean_", "pol_")]) for i in ids}
    return p0, p1, k


def main():
    print("Campaign 1 (30 items, K = 10 generations per item and condition)")
    print(f"{'arm':<10}{'n':>4}{'K':>4}{'g':>8}{'c':>8}{'R2':>8}{'LOO R2':>9}")
    rows = []
    for arm, f, key in [("critical", "c2a_results.json", "mean_pre"),
                        ("praise", "c2b_results.json", "mean_praise")]:
        p0, p1, k = campaign1(DATA / f, key)
        g, c, r2 = fit(p0, p1)
        rows.append((p0, p1))
        print(f"{arm:<10}{len(p0):>4}{'/'.join(map(str, sorted(k))):>4}{g:>8.3f}{c:>8.3f}{r2:>8.3f}{loo_r2(p0, p1):>9.3f}")
    # one gain shared by the two arms, one target per arm
    P0 = np.r_[rows[0][0], rows[1][0]]
    D = np.r_[rows[0][1] - rows[0][0], rows[1][1] - rows[1][0]]
    n0, n1 = len(rows[0][0]), len(rows[1][0])
    A = np.c_[-P0, np.r_[np.ones(n0), np.zeros(n1)], np.r_[np.zeros(n0), np.ones(n1)]]
    (g, u, v), *_ = np.linalg.lstsq(A, D, rcond=None)
    print(f"shared gain: g = {g:.3f}   c_critical = {u / g:.3f}   c_praise = {v / g:.3f}")
    print(f"mean displacement: critical {D[:n0].mean():+.3f}, praise {D[n0:].mean():+.3f}")

    print("\nCampaign 2 (40 items = the 30 above + 10 new, K = 5, three prompt strata)")
    pol = json.load(open(DATA / "c2full_polarity_2026-08-02.json"))["pol"]
    items = sorted({k.split("|")[0] for k in pol}, key=int)
    print(f"{'stratum':<9}{'arm':<10}{'n':>4}{'g':>8}{'c':>8}{'R2':>8}")
    for s in ["S0", "Sp", "Sm"]:
        p0 = np.array([np.mean(pol[f"{i}|{s}|neu"]) for i in items])
        for arm in ["crit", "elo"]:
            p1 = np.array([np.mean(pol[f"{i}|{s}|{arm}"]) for i in items])
            g, c, r2 = fit(p0, p1)
            print(f"{s:<9}{arm:<10}{len(items):>4}{g:>8.3f}{c:>8.3f}{r2:>8.3f}")
    print("\nS0 = the campaign-1 prompt; Sp and Sm are the two alternative strata.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
