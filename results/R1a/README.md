# R1a: an open-weights judge from another family, on the released responses

Preregistered in [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](../../preregistrations/2026-11-02_follow-up_runs_R1-R5.md) §3 R1. Archived on Zenodo before any data: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831). Counts corrected by the dated [erratum](../../preregistrations/2026-11-02_erratum_counts.md). The run targets one limit of campaign 1: a single judge family.

**What was run.** The released campaign-1 responses of Llama-3.1-8B-Instruct ([`data/c2a_generations.json`](../../data/c2a_generations.json) and [`data/c2b_generations.json`](../../data/c2b_generations.json)) were read by **Qwen2.5-7B-Instruct** (GGUF Q4_K_M, llama.cpp on CPU) instead of `claude-opus-4-6`.
- **Prompt:** the original judge prompt, with the full response substituted. The prompt is identified by SHA-256 `6c95c1c0…` and is not released.
- **Format:** Qwen's chat template, default system message kept.
- **Reading:** r = Σ k·p(k) / Σ p(k) over the tokens "1"–"5" at the first assistant token.
- **Sample:** the timing trial averaged 5.70 s per reading, above the preregistered 5.0 s threshold, so the reduced sample applied: every item, condition and arm at k ∈ {0, 1, 2}. That gives 360 readings: 30 items, K = 3 per condition and arm.
- **Run:** 08:18–09:28 UTC, 2 November 2026. The digit mass was 1.0000 in every reading.

## Result

| arm | g [95 % CI] | ĉ [95 % CI] | R² / leave-one-out | mean Δ [95 % CI] | slope vs. permutation null | moving items toward ĉ |
|---|---|---|---|---|---|---|
| critical | 0.740 [0.567, 0.953] | 2.349 [2.112, 2.580] | 0.700 / 0.649 | −0.619 [−0.902, −0.360] | p = 6.6 × 10⁻³ | 22 / 30 (p = 0.33) |
| praise | 0.733 [0.530, 0.915] | 3.338 [3.108, 3.565] | 0.700 / 0.652 | +0.030 [−0.264, +0.320] | p = 2.5 × 10⁻⁵ | 25 / 30 (p = 0.011) |

Preregistered criteria: **C1 (attraction) and C2 (two destinations) hold**, so outcome A. The C2 margin is 3.108 − 2.580 = **0.528**. That is about five times the shift a change of llama.cpp implementation produced in the C2 margin of [R2](../R2/README.md), where it went from +0.062 to −0.041, a change of 0.103. Targets 0.988 apart, arm-swap p = 1.0 × 10⁻⁴; shared g = 0.736 [0.618, 0.854]. Full output: [`R1a_output_sample360.txt`](R1a_output_sample360.txt).

**Reading.**
- On the same responses, a judge with open weights from another family finds the attraction and the two destinations that the original judge found.
- The gains match campaign 1 (0.74 and 0.73 here, 0.72 and 0.68 there).
- The targets sit higher on Qwen's scale (2.35 and 3.34, against 1.46 and 2.94). Amplitude agreement across readers was not a criterion (§0).
- The "single judge family" limit recedes accordingly, for this reader, this quantisation and this sample. R1b, a 72B reader on all 1 200 responses, is running.

## Verification

- **Reproduce the analysis:** `python3 -I code/check_results.py` reruns the frozen analysis on [`R1a_input_sample360.json`](R1a_input_sample360.json) and compares the result with the published output. CI runs it on every push.
- **Independent recomputation before publication:** a fresh instance worked from the raw files only.
  - Verdict: **conforming with reservations**. Report SHA-256 `edb41478c3ffd81c8e0498242f31f9c58341918c97318d44b6ce625e81b22d21`, private, because it contains the judge prompt.
  - What it checked: it recomputed the reader's weights hash in full and reconstructed the 360 prompts byte for byte, also through the chat template embedded in the weights file. It found p, mass, r and argmax consistent, replayed 5 readings bit-identically, and rebuilt the analysis input and output byte for byte.
  - Its reservations, all addressed: the count error now has a dated note (the erratum); the script hash list now names the version that ran; and the text of the prompts is kept in a private companion file, whose hashes match those logged during the run (360 of 360).
- **Kept but not released,** identified by SHA-256:
  - readings: `102a59daf6cab5c2af6735d791053af51e1a69fe0fd7d8e1f2e11b7827534a42`
  - analysis input: `7b8bdfcc716744cc…`
  - analysis output: `2475703911201e3b…`
  - report: `0a9ea4d966cbd196…`
  - all in a private repository at commit `ce7aba5`.
- **Reader:** `Qwen2.5-7B-Instruct-Q4_K_M.gguf`, SHA-256 `65b8fcd92af6b4fefa935c625d1ac27ea29dcb6ee14589c55a8f115ceaaa1423`, run with llama-cpp-python 0.3.36.
