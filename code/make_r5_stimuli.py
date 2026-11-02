#!/usr/bin/env python3
"""Build the R5 stimulus files from the released campaign-1 responses, deterministically.

    python3 -I code/make_r5_stimuli.py            # write preregistrations/R5_materials/*.csv
    python3 -I code/make_r5_stimuli.py --check    # rebuild in memory and compare byte for byte

As preregistered (section 3 R5): 240 released responses, the 30 items x {neutral, pressured} x two arms x k in {0, 1};
five readers per response; two attention checks with unambiguous polarity. Readers see only `text`; columns prefixed
META_ are hidden from participants by Prolific's AI Task Builder.

Files:
  R5_stimuli.csv  240 responses + 2 attention checks, one row each (for a builder that sets readers per item itself).
  R5_groups.csv   30 groups of 42 rows: each group is one reader's session, 40 responses and the 2 checks, shuffled;
                  over the 30 groups each response appears exactly 5 times, never twice in a group (5 rounds, each a
                  shuffle of the 240 responses cut into 6 groups of 40).
"""
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "preregistrations" / "R5_materials"
SEED = 20261105
ARMS = {"critical": ("data/c2a_generations.json", "hate"), "praise": ("data/c2b_generations.json", "praise")}
CHECKS = [
    ("ATT_NEG", "This text is poor. The argument is confused, the writing is clumsy, and nothing in it is convincing. "
                "Overall, my assessment is clearly negative: it is a bad text.", "1,2"),
    ("ATT_POS", "This text is excellent. The argument is clear, the writing is elegant, and every point is convincing. "
                "Overall, my assessment is clearly positive: it is a good text.", "4,5"),
]
FIELDS = ["id", "text", "META_TASK_GROUP_ID", "META_item", "META_arm", "META_condition", "META_k", "META_resp_sha256", "META_valid_answers"]


def responses():
    out = []
    for arm, (rel, pressed) in ARMS.items():
        rows = json.loads((ROOT / rel).read_text())["rows"]
        for r in rows:
            if int(r["k"]) in (0, 1) and int(r["item"]) < 30:
                cond = "neutral" if r["cond"] == "neutral" else "pressure"
                assert r["cond"] in ("neutral", pressed)
                out.append({"item": int(r["item"]), "arm": arm, "condition": cond, "k": int(r["k"]), "text": r["resp"]})
    out.sort(key=lambda s: (s["arm"], s["item"], s["condition"], s["k"]))
    assert len(out) == 240 and len({(s["arm"], s["item"], s["condition"], s["k"]) for s in out}) == 240
    return out


def to_csv(rows):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build():
    rng = np.random.default_rng(SEED)
    stim = responses()
    ids = rng.permutation(len(stim))  # anonymous ids that do not follow item, arm or condition
    rows = []
    for s, n in zip(stim, ids):
        rows.append({"id": f"R{int(n):03d}", "text": s["text"], "META_TASK_GROUP_ID": "", "META_item": s["item"], "META_arm": s["arm"],
                     "META_condition": s["condition"], "META_k": s["k"], "META_resp_sha256": hashlib.sha256(s["text"].encode()).hexdigest(),
                     "META_valid_answers": ""})
    checks = [{"id": cid, "text": t, "META_TASK_GROUP_ID": "", "META_item": "", "META_arm": "", "META_condition": "attention_check",
               "META_k": "", "META_resp_sha256": hashlib.sha256(t.encode()).hexdigest(), "META_valid_answers": v} for cid, t, v in CHECKS]
    single = sorted(rows, key=lambda r: r["id"]) + checks
    groups, g = [], 0
    for _ in range(5):
        order = rng.permutation(len(rows))
        for start in range(0, len(rows), 40):
            members = [dict(rows[j], META_TASK_GROUP_ID=f"G{g:02d}") for j in order[start:start + 40]]
            members += [dict(c, META_TASK_GROUP_ID=f"G{g:02d}") for c in checks]
            groups.extend(members[j] for j in rng.permutation(len(members)))
            g += 1
    counts = {}
    for r in groups:
        if r["META_condition"] != "attention_check":
            counts[r["id"]] = counts.get(r["id"], 0) + 1
    assert g == 30 and len(groups) == 30 * 42 and set(counts.values()) == {5} and len(counts) == 240
    for gid in {r["META_TASK_GROUP_ID"] for r in groups}:
        ids_in = [r["id"] for r in groups if r["META_TASK_GROUP_ID"] == gid]
        assert len(ids_in) == len(set(ids_in)) == 42
    return {"R5_stimuli.csv": to_csv(single), "R5_groups.csv": to_csv(groups)}


def main():
    files = build()
    if "--check" in sys.argv[1:]:
        bad = [n for n, t in files.items() if not (OUT / n).exists() or (OUT / n).read_text() != t]
        if bad:
            sys.exit(f"R5 STIMULI CHECK FAILED: {', '.join(bad)}")
        print(f"R5 STIMULI CHECK PASSED: {len(files)} files rebuilt identically from data/")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for n, t in files.items():
        (OUT / n).write_text(t)
        print(f"wrote {(OUT / n).relative_to(ROOT)}  sha256 {hashlib.sha256(t.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
