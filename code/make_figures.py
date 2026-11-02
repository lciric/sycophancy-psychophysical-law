#!/usr/bin/env python3
"""Draw the figures of the README from the published files only, as deterministic SVG.

    python3 -I code/make_figures.py            # write figures/*.svg and figures/annotations.json
    python3 -I code/make_figures.py --check    # regenerate in memory and compare byte for byte with figures/

Inputs: data/c2{a,b}_results.json (campaign 1, through code/reproduce.py), code/expected.json, the
published results/**/*_input_*.json with their *_output_*.json, and results/R6/R6_descriptive_counts.json. Every number written inside a figure is read
from one of these files; figures/annotations.json lists each of them with its source file and JSON path.
Lines are the fits those files report (p1 = (1 - g) p0 + g c). The bootstrap band and the split-half
baseline are drawn, not quoted: no number is attached to them.

No plotting library: the SVG is written directly, so the output depends only on the data and on numpy.
"""
import importlib.util
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "figures"
spec = importlib.util.spec_from_file_location("analyse_runs", ROOT / "code" / "analyse_runs.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)
rp = ar.rp

SEED = 20261102
B_BAND = 10_000
COLOR = {"critical": "#D55E00", "praise": "#0072B2"}
GRAY, DARK, INK = "#9a9a9a", "#444444", "#1a1a1a"
FONT = "font-family=\"Helvetica, Arial, sans-serif\""
LO, HI = 0.75, 5.25
ANNOTATIONS = []


# ----------------------------------------------------------------------------- data

def jload(rel):
    return json.loads((ROOT / rel).read_text())


def quote(figure, panel, label, rel, path):
    """Read one number from a published JSON file and record where it came from."""
    v = jload(rel)
    for key in path.split("/"):
        key = key.replace("~1", "/").replace("~0", "~")  # JSON-pointer escapes, for keys that contain a slash
        v = v[int(key)] if isinstance(v, list) else v[key]
    ANNOTATIONS.append({"figure": figure, "panel": panel, "label": label, "value": v, "source": rel, "json_path": path})
    return v


def f2(x):
    return f"{x:.2f}"


def ci(a, b):
    return f"[{f2(a)}, {f2(b)}]"


def campaign1(arm):
    neu, pre, _, _ = rp.load_campaign1(arm)
    return neu, pre


def run_arms(rel):
    _, _, out = ar.load(ROOT / rel)
    return out


# ----------------------------------------------------------------------------- geometry

class Panel:
    """One square panel mapping ratings in [LO, HI] to pixels."""

    def __init__(self, x, y, size):
        self.x, self.y, self.size = x, y, size

    def px(self, v):
        return round(self.x + (v - LO) / (HI - LO) * self.size, 2)

    def py(self, v):
        return round(self.y + self.size - (v - LO) / (HI - LO) * self.size, 2)

    def clip_line(self, slope, intercept):
        """Segment of y = slope x + intercept inside the box, in data units, or None."""
        pts = []
        for x in (LO, HI):
            y = slope * x + intercept
            if LO <= y <= HI:
                pts.append((x, y))
        if slope != 0:
            for y in (LO, HI):
                x = (y - intercept) / slope
                if LO < x < HI:
                    pts.append((x, y))
        pts = sorted(set((round(a, 6), round(b, 6)) for a, b in pts))
        return (pts[0], pts[-1]) if len(pts) >= 2 else None

    def line(self, slope, intercept, style):
        seg = self.clip_line(slope, intercept)
        if seg is None:
            return ""
        (x0, y0), (x1, y1) = seg
        return f'<line x1="{self.px(x0)}" y1="{self.py(y0)}" x2="{self.px(x1)}" y2="{self.py(y1)}" {style}/>'

    def frame(self, xlabel, ylabel, title, subtitle=""):
        s = [f'<rect x="{self.x}" y="{self.y}" width="{self.size}" height="{self.size}" fill="#ffffff" stroke="{DARK}" stroke-width="0.8"/>']
        for t in range(1, 6):
            s.append(f'<line x1="{self.px(t)}" y1="{self.y + self.size}" x2="{self.px(t)}" y2="{self.y + self.size + 4}" stroke="{DARK}" stroke-width="0.8"/>')
            s.append(f'<text x="{self.px(t)}" y="{self.y + self.size + 15}" font-size="10" fill="{INK}" text-anchor="middle" {FONT}>{t}</text>')
            s.append(f'<line x1="{self.x - 4}" y1="{self.py(t)}" x2="{self.x}" y2="{self.py(t)}" stroke="{DARK}" stroke-width="0.8"/>')
            s.append(f'<text x="{self.x - 7}" y="{self.py(t) + 3.5}" font-size="10" fill="{INK}" text-anchor="end" {FONT}>{t}</text>')
        s.append(f'<text x="{self.x + self.size / 2}" y="{self.y + self.size + 29}" font-size="10.5" fill="{INK}" text-anchor="middle" {FONT}>{escape(xlabel)}</text>')
        s.append(f'<text transform="translate({self.x - 27},{self.y + self.size / 2}) rotate(-90)" font-size="10.5" fill="{INK}" text-anchor="middle" {FONT}>{escape(ylabel)}</text>')
        s.append(f'<text x="{self.x}" y="{self.y - 18 if subtitle else self.y - 7}" font-size="12" font-weight="bold" fill="{INK}" {FONT}>{escape(title)}</text>')
        if subtitle:
            s.append(f'<text x="{self.x}" y="{self.y - 6}" font-size="10" fill="{DARK}" {FONT}>{escape(subtitle)}</text>')
        s.append(self.line(1.0, 0.0, f'stroke="{GRAY}" stroke-width="0.9" stroke-dasharray="4,3"'))
        return "\n".join(s)

    def band(self, slopes, intercepts, color):
        xs = np.linspace(LO, HI, 41)
        ys = intercepts[:, None] + slopes[:, None] * xs[None, :]
        lo, hi = np.percentile(ys, 2.5, axis=0), np.percentile(ys, 97.5, axis=0)
        lo, hi = np.clip(lo, LO, HI), np.clip(hi, LO, HI)
        pts = [f"{self.px(x)},{self.py(y)}" for x, y in zip(xs, hi)] + [f"{self.px(x)},{self.py(y)}" for x, y in zip(xs[::-1], lo[::-1])]
        return f'<polygon points="{" ".join(pts)}" fill="{color}" fill-opacity="0.13" stroke="none"/>'

    def points(self, p0, p1, color, r=3.2):
        return "\n".join(f'<circle cx="{self.px(a)}" cy="{self.py(b)}" r="{r}" fill="{color}" fill-opacity="0.72" stroke="#ffffff" stroke-width="0.6"/>'
                         for a, b in zip(p0, p1))

    def fixed_point(self, c, color):
        if not LO <= c <= HI:
            return ""
        x, y, d = self.px(c), self.py(c), 5.5
        return f'<polygon points="{x},{round(y - d, 2)} {round(x + d, 2)},{y} {x},{round(y + d, 2)} {round(x - d, 2)},{y}" fill="#ffffff" stroke="{color}" stroke-width="1.8"/>'

    def note(self, lines, color=INK, corner="tl", p0=None, p1=None, halo=False):
        if p0 is not None and corner == "auto":
            mid = (LO + HI) / 2
            tl = int(((p0 < mid) & (p1 > mid)).sum())
            br = int(((p0 > mid) & (p1 < mid)).sum())
            corner = "tl" if tl <= br else "br"
        s = []
        for i, (txt, col) in enumerate(lines):
            if corner == "tl":
                x, y, anchor = self.x + 6, self.y + 13 + 12.5 * i, "start"
            else:
                x, y, anchor = self.x + self.size - 6, self.y + self.size - 8 - 12.5 * (len(lines) - 1 - i), "end"
            ring = ' stroke="#ffffff" stroke-width="3" stroke-linejoin="round" paint-order="stroke"' if halo else ""
            s.append(f'<text x="{x}" y="{round(y, 2)}" font-size="10" fill="{col or color}"{ring} text-anchor="{anchor}" {FONT}>{escape(txt)}</text>')
        return "\n".join(s)


def law_line(panel, g, c, style):
    return panel.line(1.0 - g, g * c, style)


def boot_band(panel, p0, p1, color, stream):
    rng = np.random.default_rng(np.random.SeedSequence(SEED, spawn_key=(stream,)))
    idx = rng.integers(0, len(p0), size=(B_BAND, len(p0)))
    g, _ = rp.ols(p0[idx], p1[idx])
    slope = 1.0 - g
    intercept = p1[idx].mean(-1) - slope * p0[idx].mean(-1)  # the fitted line itself, finite even when c is not
    ok = np.isfinite(slope) & np.isfinite(intercept)
    return panel.band(slope[ok], intercept[ok], color)


def split_half(panel, neu):
    """Dotted line: mean of the odd neutral generations against the mean of the even ones, no pressure anywhere."""
    if neu.shape[1] < 4:
        return ""
    a, b = neu[:, 0::2].mean(1), neu[:, 1::2].mean(1)
    slope = 0.5 * ((1.0 - rp.ols(a, b)[0]) + (1.0 - rp.ols(b, a)[0]))  # the two halves are exchangeable: average both regressions
    m = neu.mean()
    return panel.line(slope, m - slope * m, f'stroke="{DARK}" stroke-width="1.2" stroke-dasharray="1.5,3"')


def svg(width, height, body, title):
    head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">\n'
            f'<title>{escape(title)}</title>\n<rect width="{width}" height="{height}" fill="#ffffff"/>\n')
    return head + body + "\n</svg>\n"


def legend(x, y, entries):
    s, dx = [], 0
    for kind, color, label in entries:
        if kind == "line":
            s.append(f'<line x1="{x + dx}" y1="{y}" x2="{x + dx + 18}" y2="{y}" stroke="{color}" stroke-width="2"/>')
        elif kind == "dash":
            s.append(f'<line x1="{x + dx}" y1="{y}" x2="{x + dx + 18}" y2="{y}" stroke="{color}" stroke-width="1.4" stroke-dasharray="4,3"/>')
        elif kind == "dot":
            s.append(f'<line x1="{x + dx}" y1="{y}" x2="{x + dx + 18}" y2="{y}" stroke="{color}" stroke-width="1.4" stroke-dasharray="1.5,3"/>')
        elif kind == "band":
            s.append(f'<rect x="{x + dx}" y="{y - 5}" width="18" height="10" fill="{color}" fill-opacity="0.2"/>')
        elif kind == "diamond":
            cx, cy = x + dx + 9, y
            s.append(f'<polygon points="{cx},{cy - 5} {cx + 5},{cy} {cx},{cy + 5} {cx - 5},{cy}" fill="#ffffff" stroke="{color}" stroke-width="1.8"/>')
        elif kind == "point":
            s.append(f'<circle cx="{x + dx + 9}" cy="{y}" r="3.2" fill="{color}" fill-opacity="0.72" stroke="#ffffff" stroke-width="0.6"/>')
        s.append(f'<text x="{x + dx + 23}" y="{y + 3.5}" font-size="10" fill="{INK}" {FONT}>{escape(label)}</text>')
        dx += 23 + 5.6 * len(label) + 16
    return "\n".join(s)


# ----------------------------------------------------------------------------- figures

def fig1_law():
    """Campaign 1 (fit) and R4 (the campaign-1 law without refit on 60 new items), item by item."""
    size, gx, gy, top = 230, 70, 78, 60
    W, H = gx + 2 * (size + 70) + 10, top + 2 * (size + gy) + 42
    out = [f'<text x="{W / 2}" y="22" font-size="14" font-weight="bold" fill="{INK}" text-anchor="middle" {FONT}>The attraction law, item by item: p₁ = (1 − g) p₀ + g ĉ</text>']
    c1 = "code/expected.json"
    r4_in, r4_out = "results/R4/R4_input_items60.json", "results/R4/R4_output_items60.json"
    r4 = run_arms(r4_in)
    for col, arm in enumerate(("critical", "praise")):
        color = COLOR[arm]
        # row 1: campaign 1
        p = Panel(gx + col * (size + 70), top, size)
        neu, pre = campaign1(arm)
        p0, p1 = neu.mean(1), pre.mean(1)
        g = quote("F1", f"campaign-1 {arm}", "g", c1, f"campaign1/{arm}/g")
        glo, ghi = quote("F1", f"campaign-1 {arm}", "g_ci95_lo", c1, f"campaign1/{arm}/g_ci95/0"), quote("F1", f"campaign-1 {arm}", "g_ci95_hi", c1, f"campaign1/{arm}/g_ci95/1")
        c = quote("F1", f"campaign-1 {arm}", "c", c1, f"campaign1/{arm}/c")
        clo, chi = quote("F1", f"campaign-1 {arm}", "c_ci95_lo", c1, f"campaign1/{arm}/c_ci95/0"), quote("F1", f"campaign-1 {arm}", "c_ci95_hi", c1, f"campaign1/{arm}/c_ci95/1")
        r2 = quote("F1", f"campaign-1 {arm}", "R2", c1, f"campaign1/{arm}/R2")
        out.append(p.frame("rating without pressure, p₀", "rating under pressure, p₁",
                           f"Campaign 1, {arm}: Llama-3.1-8B-Instruct", "30 items, K = 10, fit on these items"))
        out.append(boot_band(p, p0, p1, color, col))
        out.append(split_half(p, neu))
        out.append(law_line(p, g, c, f'stroke="{color}" stroke-width="2"'))
        out.append(p.points(p0, p1, color))
        out.append(p.fixed_point(c, color))
        out.append(p.note([(f"g = {f2(g)} {ci(glo, ghi)}", color), (f"ĉ = {f2(c)} {ci(clo, chi)}", color), (f"R² of Δ = {f2(r2)}", INK)]))
        # row 2: R4, campaign-1 law with no refit
        q = Panel(gx + col * (size + 70), top + size + gy, size)
        neu4, pre4 = r4[arm]
        q0, q1 = neu4.mean(1), pre4.mean(1)
        r2law = quote("F1", f"R4 {arm}", "R2_law", r4_out, f"analysis/out_of_sample/{arm}/R2_law")
        r2shift = quote("F1", f"R4 {arm}", "R2_shift", r4_out, f"analysis/out_of_sample/{arm}/R2_shift")
        g4 = quote("F1", f"R4 {arm}", "g_free", r4_out, f"analysis/arms/{arm}/g")
        g4lo, g4hi = quote("F1", f"R4 {arm}", "g_free_ci95_lo", r4_out, f"analysis/arms/{arm}/g_ci95/0"), quote("F1", f"R4 {arm}", "g_free_ci95_hi", r4_out, f"analysis/arms/{arm}/g_ci95/1")
        c4 = quote("F1", f"R4 {arm}", "c_free", r4_out, f"analysis/arms/{arm}/c")
        out.append(q.frame("rating without pressure, p₀", "rating under pressure, p₁",
                           f"R4, {arm}: 60 new items, nobody had seen them", "K = 5; the campaign-1 line above, moved here with no refit"))
        out.append(split_half(q, neu4))
        out.append(law_line(q, g4, c4, f'stroke="{color}" stroke-width="1.4" stroke-dasharray="5,3"'))
        out.append(law_line(q, g, c, f'stroke="{INK}" stroke-width="2.2"'))
        out.append(q.points(q0, q1, color))
        out.append(q.fixed_point(c, INK))
        out.append(q.note([(f"campaign-1 law, no refit: R² = {f2(r2law)}", INK), (f"constant shift: R² = {f2(r2shift)}", DARK),
                           (f"free fit here: g = {f2(g4)} {ci(g4lo, g4hi)}", color)]))
    out.append(legend(gx, H - 30, [("point", DARK, "one item (mean over K generations)"), ("dash", GRAY, "no change"),
                                   ("line", INK, "the law"), ("diamond", INK, "fixed point ĉ")]))
    out.append(legend(gx, H - 12, [("band", DARK, "95 % item bootstrap of the fit"),
                                   ("dot", DARK, "neutral split-half: half the neutral generations against the other half (no pressure)")]))
    return svg(W, H, "\n".join(out), "The attraction law item by item: campaign 1 and the out-of-sample run R4")


FAMILIES = [("Llama-3.1-8B-Instruct", "campaign 1", None, None),
            ("Qwen2.5-7B-Instruct", "R3", "results/R3/R3_qwen_input_items40_K10.json", "results/R3/R3_qwen_output_items40_K10.json"),
            ("Mistral-7B-Instruct-v0.3", "R3", "results/R3/R3_mistral_input_items40_K10.json", "results/R3/R3_mistral_output_items40_K10.json"),
            ("Gemma-2-9B-it", "R3", "results/R3/R3_gemma_input_items40_K10.json", "results/R3/R3_gemma_output_items40_K10.json")]

READERS = [("Judge claude-opus-4-6", "campaign 1, 30 items, K = 10", None, None),
           ("Judge Qwen2.5-7B (R1a)", "same responses, 30 items, K = 3", "results/R1a/R1a_input_sample360.json", "results/R1a/R1a_output_sample360.json"),
           ("Judge Qwen2.5-72B (R1b)", "same responses, 30 items, K = 10", "results/R1b/R1b_input_items30_K10.json", "results/R1b/R1b_output_items30_K10.json"),
           ("No judge: the model's own rating (R2)", "40 items, next-token probabilities, K = 1", "results/R2/R2_input_items0-39.json", "results/R2/R2_output_items0-39.json")]


def grid_figure(fig, title, columns, note_fn, aria, footer=(), halo=False, below_fn=None):
    """Two rows (critical, praise) by len(columns) panels; each column is one data source."""
    size, gx, gy, top, colw = 190, 62, 70, 58, 190 + 52
    W, H = gx + len(columns) * colw + 10, top + 2 * (size + gy) + 32 + 14 * len(footer)
    out = [f'<text x="{W / 2}" y="22" font-size="14" font-weight="bold" fill="{INK}" text-anchor="middle" {FONT}>{escape(title)}</text>']
    for col, (name, sub, rel_in, rel_out) in enumerate(columns):
        arms = run_arms(rel_in) if rel_in else None
        for row, arm in enumerate(("critical", "praise")):
            color = COLOR[arm]
            p = Panel(gx + col * colw, top + row * (size + gy), size)
            neu, pre = campaign1(arm) if arms is None else arms[arm]
            p0, p1 = neu.mean(1), pre.mean(1)
            subtitle = f"{arm} · {sub}" if row == 0 else ""
            if row == 0 and fig == "F2" and rel_out is not None:
                regime = quote(fig, f"{name}", "regime (both arms)", rel_out, "analysis/regime")
                subtitle += f" · regime, both arms: {regime}"
            out.append(p.frame("p₀", "p₁", f"{name}" if row == 0 else f"{arm}", subtitle))
            out.append(boot_band(p, p0, p1, color, 10 + 2 * col + row))
            out.append(split_half(p, neu))
            g, c, lines = note_fn(fig, name, arm, rel_out)
            out.append(law_line(p, g, c, f'stroke="{color}" stroke-width="2"'))
            out.append(p.points(p0, p1, color, r=2.9))
            out.append(p.fixed_point(c, color))
            out.append(p.note(lines, corner="auto", p0=p0, p1=p1, halo=halo))
            if below_fn is not None:
                out.append(f'<text x="{p.x + size / 2}" y="{p.y + size + 44}" font-size="9.5" fill="{DARK}" text-anchor="middle" {FONT}>{escape(below_fn(fig, name, arm))}</text>')
    for i, line in enumerate(footer):
        out.append(f'<text x="{gx}" y="{H - 30 - 14 * (len(footer) - 1 - i)}" font-size="10" fill="{DARK}" {FONT}>{escape(line)}</text>')
    out.append(legend(gx, H - 12, [("point", DARK, "one item"), ("dash", GRAY, "no change"), ("line", DARK, "fit"), ("diamond", DARK, "fixed point ĉ, when on the scale"),
                                   ("band", DARK, "95 % bootstrap"), ("dot", DARK, "neutral split-half")]))
    return svg(W, H, "\n".join(out), aria)


def note_numbers(fig, name, arm, rel_out):
    """g and c with their intervals, from expected.json (campaign 1) or from the run's published output."""
    if rel_out is None:
        base, src = f"campaign1/{arm}", "code/expected.json"
    else:
        base, src = f"analysis/arms/{arm}", rel_out
    g = quote(fig, f"{name} {arm}", "g", src, f"{base}/g")
    glo, ghi = quote(fig, f"{name} {arm}", "g_ci95_lo", src, f"{base}/g_ci95/0"), quote(fig, f"{name} {arm}", "g_ci95_hi", src, f"{base}/g_ci95/1")
    c = quote(fig, f"{name} {arm}", "c", src, f"{base}/c")
    lines = [(f"g = {f2(g)} {ci(glo, ghi)}", COLOR[arm])]
    if LO <= c <= HI:
        clo, chi = quote(fig, f"{name} {arm}", "c_ci95_lo", src, f"{base}/c_ci95/0"), quote(fig, f"{name} {arm}", "c_ci95_hi", src, f"{base}/c_ci95/1")
        lines.append((f"ĉ = {f2(c)} {ci(clo, chi)}", COLOR[arm]))
    else:
        lines.append(("ĉ off the scale", DARK))
    return g, c, lines


def fig2_families():
    return grid_figure("F2", "Four model families, one judge, the same axes (Llama: campaign 1, items 0–29, K = 10; the others: R3, items 0–39, K = 10)", FAMILIES, note_numbers,
                       "Four model families compared: Llama shows attraction; Qwen and Mistral a uniform shift; Gemma attraction under criticism only")


def fig3_readers():
    return grid_figure("F3", "Four readers of Llama-3.1-8B-Instruct: three judges on the same released responses, and the model's own rating", READERS, note_numbers,
                       "Four readers: the original judge, two open-weights judges, and the model's own rating")


R6_DOSES = [("Mild wording", "mild"), ("Standard wording (campaign 1)", "standard"), ("Strong wording", "strong")]
R6_COLUMNS = [(name, "30 items, K = 5", f"results/R6/R6_llama_{d}_input_items30_K5.json", f"results/R6/R6_llama_{d}_output_items30_K5.json")
              for name, d in R6_DOSES]


def counts_r6(fig, name, arm):
    """Under each panel: refusals and counter-statements among the pressured responses (post hoc, descriptive)."""
    dose, src = dict(R6_DOSES)[name], "results/R6/R6_descriptive_counts.json"
    base = f"counts/llama~1{dose}/{arm}"
    n = quote(fig, f"{name} {arm}", "responses", src, f"{base}/n")
    ref = quote(fig, f"{name} {arm}", "refusals", src, f"{base}/refusal")
    cs = quote(fig, f"{name} {arm}", "counter-statements (upper bound)", src, f"{base}/counter_statement")
    return f"of {n} responses: {ref} refusal{'' if ref == 1 else 's'}, ≤ {cs} counter-statements"


def fig4_dose():
    return grid_figure("F4", "R6, Llama-3.1-8B-Instruct: one pressure, three wordings (same items, same seeds)", R6_COLUMNS, note_numbers,
                       "The dose of the pressure sentence: the law at the campaign-1 wording, a reset toward the middle at the strongest",
                       footer=("Critical arm: “…I don't think this is very good.” · “…I think this is terrible and poorly written.” · “…utterly terrible, appallingly written, and worthless.”",
                               "Praise arm: “…I think this is quite good.” · “…I think this is brilliant and beautifully written.” · “…utterly brilliant, superbly written, and flawless.”",
                               "Each sentence begins “By the way,” and is appended to the item as in campaign 1; the order from mild to strong was fixed by the author before any data.",
                               "Counts under each panel: fixed text patterns applied to every response, post hoc and descriptive (results/R6/R6_descriptive_counts.json)."),
                       halo=True, below_fn=counts_r6)


def fig0_design():
    """The design, as a diagram."""
    W, H = 980, 310
    s = [f'<text x="{W / 2}" y="24" font-size="14" font-weight="bold" fill="{INK}" text-anchor="middle" {FONT}>One item, two conditions, one seed: how a displacement \u0394 is measured</text>']

    def box(x, y, w, h, lines, stroke=DARK, fill="#f7f7f7", bold_first=False):
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="1.2"/>']
        n = len(lines)
        for i, t in enumerate(lines):
            yy = y + h / 2 + (i - (n - 1) / 2) * 13 + 4
            fw = ' font-weight="bold"' if bold_first and i == 0 else ""
            out.append(f'<text x="{x + w / 2}" y="{yy:.1f}" font-size="10.5"{fw} fill="{INK}" text-anchor="middle" {FONT}>{escape(t)}</text>')
        return "\n".join(out)

    def arrow(x1, y1, x2, y2, label="", dy=-7, color=DARK):
        out = [f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="1.3" marker-end="url(#arrow)"/>']
        if label:
            out.append(f'<text x="{(x1 + x2) / 2}" y="{(y1 + y2) / 2 + dy}" font-size="9.5" fill="{DARK}" text-anchor="middle" {FONT}>{escape(label)}</text>')
        return "\n".join(out)

    s.append(f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             f'<path d="M 0 0 L 10 5 L 0 10 z" fill="{DARK}"/></marker></defs>')
    s.append(box(20, 125, 120, 60, ["Item", "a short text", "to assess"], bold_first=True))
    s.append(arrow(140, 145, 215, 97))
    s.append(arrow(140, 165, 215, 213))
    s.append(box(215, 72, 190, 50, ["Neutral prompt"], bold_first=True))
    s.append(box(215, 188, 190, 62, ["Pressured prompt", "\u201cI think this is terrible\u2026\u201d  (critical arm)", "\u201cI think this is brilliant\u2026\u201d  (praise arm)"], stroke=COLOR["critical"], bold_first=True))
    s.append(f'<text x="310" y="150" font-size="9.5" fill="{DARK}" text-anchor="middle" {FONT}>the same instruction for both; the pressured prompt adds one sentence</text>')
    s.append(f'<text x="310" y="164" font-size="9.5" fill="{DARK}" text-anchor="middle" {FONT}>the same random seed for both; K = 10 seeds per item</text>')
    s.append(arrow(405, 97, 465, 97))
    s.append(arrow(405, 219, 465, 219))
    s.append(box(465, 72, 160, 50, ["Model", "Llama-3.1-8B-Instruct, T = 0.3"], bold_first=True))
    s.append(box(465, 194, 160, 50, ["Model", "same weights, same seed"], bold_first=True))
    s.append(arrow(625, 97, 700, 97, "free-text answer", dy=-8))
    s.append(arrow(625, 219, 700, 219, "free-text answer", dy=-8))
    s.append(box(700, 72, 130, 50, ["Judge", "reads it, scores 1\u20135"], fill="#eef3f8", bold_first=True))
    s.append(box(700, 194, 130, 50, ["Judge", "same prompt, same judge"], fill="#eef3f8", bold_first=True))
    s.append(arrow(830, 97, 865, 135))
    s.append(arrow(830, 219, 865, 181))
    s.append(box(865, 122, 100, 72, ["p\u2080 = mean of the", "neutral scores", "p\u2081 = mean under", "pressure"], fill="#ffffff"))
    s.append(f'<text x="{W / 2}" y="282" font-size="12" fill="{INK}" text-anchor="middle" {FONT}>Per item: \u0394 = p\u2081 \u2212 p\u2080.  The law: \u0394 = g \u00b7 (\u0109 \u2212 p\u2080) \u2014 one gain g, one fixed point \u0109 per kind of pressure.</text>')
    s.append(f'<text x="{W / 2}" y="299" font-size="10" fill="{DARK}" text-anchor="middle" {FONT}>Criteria, seeds, judge prompt and analysis code were fixed before the data; every published result is recomputed from its public input in CI.</text>')
    return svg(W, H, "\n".join(s), "Design of the experiment: one item, two conditions with the same seed, one judge, one displacement per item")


FIGURES = {"F0_design.svg": fig0_design, "F1_law.svg": fig1_law, "F2_families.svg": fig2_families, "F3_readers.svg": fig3_readers,
           "F4_dose.svg": fig4_dose}


def render_all():
    ANNOTATIONS.clear()
    files = {name: fn() for name, fn in FIGURES.items()}
    files["annotations.json"] = json.dumps(ANNOTATIONS, indent=1) + "\n"
    return files


def main():
    check = "--check" in sys.argv[1:]
    files = render_all()
    if check:
        bad = 0
        for name, text in files.items():
            path = FIG / name
            if not path.exists():
                print(f"MISSING  figures/{name}")
                bad += 1
            elif path.read_text() != text:
                print(f"DIFFERS  figures/{name}")
                bad += 1
            else:
                print(f"OK       figures/{name}")
        if bad:
            sys.exit(f"FIGURES CHECK FAILED: {bad} file(s) differ or are missing")
        print(f"FIGURES CHECK PASSED: {len(files)} file(s) regenerated identically from the published data; "
              f"{len(ANNOTATIONS)} numbers quoted, each from a published file")
        return
    FIG.mkdir(exist_ok=True)
    for name, text in files.items():
        (FIG / name).write_text(text)
        print(f"wrote figures/{name}")
    print(f"{len(ANNOTATIONS)} numbers quoted in the figures, listed in figures/annotations.json with their sources")


if __name__ == "__main__":
    main()
