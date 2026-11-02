# R2: the model's own rating, without any judge

Preregistered in [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](../../preregistrations/2026-11-02_follow-up_runs_R1-R5.md) §3 (archived on Zenodo before any data: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831)). It targets one limit of campaign 1: there the verdict was read by a judge model.

**What was run.** Llama-3.1-8B-Instruct (GGUF Q4_K_M, llama.cpp on CPU) received the campaign-1 system prompt and instruction, asked for a digit from 1 to 5, without pressure and with each campaign-1 suffix. The reading is the subject's own next-token probabilities over "1"–"5" at the first assistant position, r = Σ k·p(k) / Σ p(k). K = 1 (deterministic). Items 0–39 are the primary set, items 0–199 a descriptive pass. Run from 07:29 to 08:15 UTC, 2 November 2026, with 600 readings and no digit mass below 0.5.

## Result (items 0–39, primary)

| arm | g [95 % CI] | ĉ [95 % CI] | R² / leave-one-out | mean Δ [95 % CI] |
|---|---|---|---|---|
| critical | 0.625 [0.569, 0.680] | 2.871 [2.800, 2.930] | 0.911 / 0.902 | −0.540 [−0.667, −0.403] |
| praise | 0.137 [0.029, 0.242] | 3.724 [2.992, 5.047] | 0.090 / 0.013 | −0.002 [−0.093, +0.090] |

Preregistered criteria: **C1 (attraction) holds; C2 (two destinations) holds**, so outcome A, regime "attraction". Targets 0.852 apart (arm-swap p = 1.0 × 10⁻⁴). Full output: [`R2_output_items0-39.txt`](R2_output_items0-39.txt). Items 0–199, descriptive only: critical g = 0.638 [0.600, 0.675], praise g = 0.129 [0.071, 0.189] ([`R2_output_items0-199.txt`](R2_output_items0-199.txt)).

**Reading.**
- Without any judge, the model's own rating reproduces the attraction under criticism, with a tight fit.
- Under praise the rating barely moves: g = 0.14, against 0.68 when a judge read the free-text verdicts of campaign 1. With g that small, ĉ_praise is poorly determined.
- The praise margins are thin: the lower bound of g is 0.029, and C2 passes by 0.062 between the two ĉ intervals.

## Sensitivity to the inference build (post hoc, descriptive)

The 120 primary readings were replayed with llama-cpp-python 0.3.16 instead of 0.3.36, with the same weights and the same prompts (byte-identical on a 24-reading sample), then analysed by the same frozen code. The two series agree closely: r = 0.9985 over the 160 pairs, with median |Δr| 0.021, maximum 0.112, and mean signed difference +0.004.

| arm | run (0.3.36): g; ĉ | replay (0.3.16): g; ĉ |
|---|---|---|
| critical | 0.625 [0.569, 0.680]; 2.871 [2.800, **2.930**] | 0.639 [0.585, 0.690]; 2.890 [2.821, **2.945**] |
| praise | 0.137 [0.029, 0.242]; 3.724 [**2.992**, 5.047] | 0.144 [0.037, 0.254]; 3.655 [**2.904**, 4.644] |
| criteria | C1 true; C2 true (margin +0.062) | C1 true; **C2 false** (overlap 0.041) |

C1 holds under both builds. C2 passes on the preregistered run but fails under the second build. **Two destinations are therefore not robustly established in the model's own rating.** The preregistered verdict stays the run's; this section does not requalify it. Files: [`R2_sensitivity_llamacpp0.3.16_input_items0-39.json`](R2_sensitivity_llamacpp0.3.16_input_items0-39.json) and its output. The replay kept r but not the five probabilities, so these 120 values cannot be recomputed from p. An independent re-check of this section was still running when it was published (2 November, 10:10 Paris).

## Verification

- **Reproduce the analysis:** `python3 -I code/check_results.py` reruns the frozen `code/analyse_runs.py` on every published input and compares the result with the published output, value for value. CI runs it on every push.
- **Independent recomputation of the run, before publication:** a fresh model instance worked from the raw files only. It reconstructed the 600 prompts byte for byte, recomputed every r with zero difference, reran the analysis, and replayed 5 readings bit-identically. Verdict: conforming on all 9 points.
- **Kept but not released:** the raw readings contain the item texts, which are not released. They are identified by SHA-256.
  - readings: `24ed5313b219a17efff1948690ecb2bdb670b55b22c27f49efe9b6b569320344`
  - corpus: `64894c215d68a4566bb0f232cf9c565285a23b3186607bdf0a436384b7a759e9`
  - weights (public, bartowski): `7b064f5842bf9532c91456deda288a1b672397a54fa729aa665952863033557c`
  - independent report: `eecfa126c2a857e1934728923d12a167cd44f3ec0c611fbe079df7831e74dd8d`
  - all of them in a private repository at commit `c6cb366`.
- **Instrument incident, before any usable data:** a first attempt read flat logits after a change in llama-cpp-python. It produced 282 uniform readings, r = 3.0 everywhere. It was rejected on that instrument criterion alone, without any criterion being computed, and is kept. R2 was then rerun from zero.
- **Reproducibility:** the readings replay exactly with llama-cpp-python 0.3.36 on the same stack, and within |Δr| ≲ 0.1 with other builds (see the sensitivity above).
