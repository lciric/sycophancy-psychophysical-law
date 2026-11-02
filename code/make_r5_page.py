#!/usr/bin/env python3
"""Build the self-contained reading page of R5 (and of its acquaintance pilot) from the session file.

    python3 -I code/make_r5_page.py --template OUT.html                       # public template, instruction left as a placeholder
    python3 -I code/make_r5_page.py --instruction INSTR.json OUT.html          # the page readers use (private: carries the instruction)

INSTR.json: {"instruction": "...", "question": "...", "label_low": "...", "label_high": "..."}, the judge prompt's scale and
wording as section 3 R5 requires. The page works offline, shows one response at a time in the order of
preregistrations/R5_materials/R5_groups.csv, keeps progress in the browser, and ends with the ratings as CSV lines
(participant_id, id, rating, session, position) to copy or download and send back. It sends nothing anywhere.
"""
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GROUPS = ROOT / "preregistrations" / "R5_materials" / "R5_groups.csv"
PLACEHOLDER = {"instruction": "[The instruction is the judge prompt's scale and wording. It is filled in the private copy of this page "
                              "given to readers, whose SHA-256 is recorded in a dated note before any reading.]",
               "question": "[question]", "label_low": "[label of 1]", "label_high": "[label of 5]"}

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reading study</title>
<style>
:root { --bg:#fbfaf7; --ink:#1d1d1f; --muted:#5f6368; --line:#d9d6cf; --accent:#1f5f8b; --card:#ffffff; --sel:#dde9f3; --warn:#8a4b00; }
@media (prefers-color-scheme: dark) { :root { --bg:#16171a; --ink:#ececec; --muted:#a3a7ad; --line:#3a3c41; --accent:#8fbde0; --card:#1f2024; --sel:#26384a; --warn:#e3a95c; } }
* { box-sizing: border-box; }
html, body { background: var(--bg); color: var(--ink); margin: 0; }
body { font: 17px/1.6 Georgia, "Times New Roman", serif; }
main { max-width: 720px; margin: 0 auto; padding: 28px 16px 72px; }
h1 { font: 600 22px/1.3 system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0 0 12px; }
p, li { margin: 0 0 12px; }
.ui { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
.muted { color: var(--muted); font-size: 14px; }
label { display: block; font: 600 14px system-ui, sans-serif; margin: 14px 0 6px; }
input[type=text] { font: 17px system-ui, sans-serif; padding: 10px 12px; width: 100%; max-width: 240px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--ink); }
button { font: 600 16px system-ui, sans-serif; padding: 11px 18px; border-radius: 8px; border: 1px solid var(--accent); background: var(--accent); color: #fff; cursor: pointer; }
button.secondary { background: transparent; color: var(--accent); }
button:disabled { opacity: .4; cursor: default; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 18px; margin: 14px 0 18px; white-space: pre-wrap; overflow-wrap: anywhere; }
.instr { white-space: pre-wrap; }
.bar { height: 6px; background: var(--line); border-radius: 3px; overflow: hidden; margin: 8px 0 4px; }
.bar > div { height: 100%; background: var(--accent); width: 0; }
.scale { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; margin: 10px 0 4px; }
.scale button { background: var(--card); color: var(--ink); border: 1px solid var(--line); padding: 14px 0; font-size: 20px; }
.scale button.on { background: var(--sel); border-color: var(--accent); outline: 2px solid var(--accent); }
.ends { display: flex; justify-content: space-between; gap: 16px; font: 13px system-ui, sans-serif; color: var(--muted); margin-bottom: 16px; }
.ends span:last-child { text-align: right; }
textarea { width: 100%; min-height: 220px; font: 13px/1.4 ui-monospace, Menlo, Consolas, monospace; padding: 10px; border: 1px solid var(--line); border-radius: 8px; background: var(--card); color: var(--ink); }
.row { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
.err { color: var(--warn); font: 14px system-ui, sans-serif; min-height: 20px; }
</style>
</head>
<body>
<main id="app" class="ui"></main>
<script>
const DATA = __DATA__;
const INSTR = __INSTR__;
const app = document.getElementById("app");
let st = null;

function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c])); }
function key() { return "r5reading:" + st.reader + ":" + st.session; }
function save() { try { localStorage.setItem(key(), JSON.stringify(st)); } catch (e) {} }
function load(reader, session) { try { const v = localStorage.getItem("r5reading:" + reader + ":" + session); return v ? JSON.parse(v) : null; } catch (e) { return null; } }

function start() {
  app.innerHTML = `<h1>Reading study</h1>
  <p>Thank you for helping. You will read short texts, one at a time, and give each one a number from 1 to 5. A session has 42 texts and takes about 35 minutes. You can close the page and come back: it remembers where you were on this device.</p>
  <label for="r">Your reader code</label><input id="r" type="text" placeholder="e.g. P03" autocomplete="off">
  <label for="s">Your session code</label><input id="s" type="text" placeholder="e.g. G07" autocomplete="off">
  <p class="err" id="e"></p>
  <button id="go">Start</button>`;
  document.getElementById("go").onclick = () => {
    const reader = document.getElementById("r").value.trim().toUpperCase();
    const session = document.getElementById("s").value.trim().toUpperCase();
    if (!/^P\d{2}$/.test(reader)) { document.getElementById("e").textContent = "The reader code looks like P03."; return; }
    if (!DATA.groups[session]) { document.getElementById("e").textContent = "Unknown session code. It looks like G07."; return; }
    st = load(reader, session) || {reader, session, pos: 0, answers: [], began: new Date().toISOString(), seenInstr: false};
    if (st.pos >= DATA.groups[session].length) return done();
    st.seenInstr ? task() : instructions();
  };
}

function instructions() {
  app.innerHTML = `<h1>Instructions</h1><div class="instr">${esc(INSTR.instruction)}</div>
  <p class="muted">Read each text in full, then choose one number. There are no right or wrong answers, only your reading. You cannot go back to a previous text. Most texts end with a technical marker, &lt;|eot_id|&gt;: ignore it.</p>
  <button id="b">Begin</button>`;
  document.getElementById("b").onclick = () => { st.seenInstr = true; save(); task(); };
}

function task() {
  const ids = DATA.groups[st.session], id = ids[st.pos], n = ids.length;
  let choice = null;
  app.innerHTML = `<div class="muted">Text ${st.pos + 1} of ${n} · session ${esc(st.session)}</div>
  <div class="bar"><div style="width:${(100 * st.pos / n).toFixed(1)}%"></div></div>
  <div class="card" style="font-family: Georgia, 'Times New Roman', serif;">${esc(DATA.texts[id])}</div>
  <p><strong>${esc(INSTR.question)}</strong></p>
  <div class="scale">${[1, 2, 3, 4, 5].map(v => `<button data-v="${v}" aria-label="${v}">${v}</button>`).join("")}</div>
  <div class="ends"><span>1 = ${esc(INSTR.label_low)}</span><span>5 = ${esc(INSTR.label_high)}</span></div>
  <button id="n" disabled>Next</button> <span class="muted">Keys 1–5 to choose, Enter to go on.</span>`;
  const buttons = [...app.querySelectorAll(".scale button")], next = document.getElementById("n");
  const pick = v => { choice = v; buttons.forEach(b => b.classList.toggle("on", +b.dataset.v === v)); next.disabled = false; };
  buttons.forEach(b => b.onclick = () => pick(+b.dataset.v));
  next.onclick = () => {
    if (choice === null) return;
    st.answers.push({id, rating: choice, position: st.pos + 1, at: new Date().toISOString()});
    st.pos += 1; save();
    st.pos >= n ? done() : task();
    window.scrollTo(0, 0);
  };
  document.onkeydown = e => { if (/^[1-5]$/.test(e.key)) pick(+e.key); if (e.key === "Enter" && choice !== null) next.click(); };
}

function done() {
  document.onkeydown = null;
  const lines = ["participant_id,id,rating,session,position"].concat(st.answers.map(a => [st.reader, a.id, a.rating, st.session, a.position].join(",")));
  const csv = lines.join("\n") + "\n";
  app.innerHTML = `<h1>Done, thank you</h1>
  <p>Please send the block below back to the person who sent you this page: copy it into an e-mail, or download the file and attach it.</p>
  <textarea id="t" readonly>${esc(csv)}</textarea>
  <div class="row"><button id="c">Copy</button><button id="d" class="secondary">Download the file</button><span class="muted" id="m"></span></div>`;
  document.getElementById("c").onclick = async () => {
    const t = document.getElementById("t");
    try { await navigator.clipboard.writeText(csv); } catch (e) { t.select(); document.execCommand("copy"); }
    document.getElementById("m").textContent = "Copied.";
  };
  document.getElementById("d").onclick = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], {type: "text/csv"}));
    a.download = `reading_${st.reader}_${st.session}.csv`; a.click();
  };
}

start();
</script>
</body>
</html>
"""


def build(instr):
    texts, groups = {}, {}
    for r in csv.DictReader(GROUPS.open()):
        texts[r["id"]] = r["text"]
        groups.setdefault(r["META_TASK_GROUP_ID"], []).append(r["id"])
    assert len(groups) == 30 and all(len(v) == 42 for v in groups.values()) and len(texts) == 242
    blob = lambda o: json.dumps(o, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")
    return PAGE.replace("__DATA__", blob({"texts": texts, "groups": groups})).replace("__INSTR__", blob(instr))


def main():
    args = sys.argv[1:]
    if args[:1] == ["--template"] and len(args) == 2:
        html, out = build(PLACEHOLDER), Path(args[1])
    elif args[:1] == ["--instruction"] and len(args) == 3:
        instr = json.loads(Path(args[1]).read_text())
        if set(instr) != set(PLACEHOLDER):
            sys.exit(f"the instruction file needs exactly the keys {sorted(PLACEHOLDER)}")
        html, out = build(instr), Path(args[2])
    else:
        sys.exit(__doc__)
    out.write_text(html)
    print(f"wrote {out}  sha256 {hashlib.sha256(html.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
