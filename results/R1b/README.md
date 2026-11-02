# R1b: a 72B open-weights judge on all 1 200 released responses

Preregistered in [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](../../preregistrations/2026-11-02_follow-up_runs_R1-R5.md) §3 R1. Archived on Zenodo before any data: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831). Counts corrected by the dated [erratum](../../preregistrations/2026-11-02_erratum_counts.md). The run targets one limit of campaign 1: a single judge family. [R1a](../R1a/README.md) ran the same procedure with a 7B reader on a reduced sample.

**What was run.** The released campaign-1 responses of Llama-3.1-8B-Instruct ([`data/c2a_generations.json`](../../data/c2a_generations.json) and [`data/c2b_generations.json`](../../data/c2b_generations.json)) were read by **Qwen2.5-72B-Instruct** instead of `claude-opus-4-6`.
- **Reader:** revision `495f39366efef23836d0cfae4fbe635880d2be31`, logged at download; bf16, transformers, sdpa attention, on two 80 GB A100 GPUs.
- **Prompt and reading:** as in R1a. The original judge prompt (SHA-256 `6c95c1c0…`, not released) carries the full response, in Qwen's chat template with its default system message. The reading is r = Σ k·p(k) / Σ p(k) over the tokens "1"–"5" at the first assistant token. On the 360 readings the two runs share, the prompts are identical to R1a's.
- **Sample:** all 1 200 responses: 30 items, 2 arms, neutral and pressured, K = 10.
- **Run:** 10:28–10:34 UTC, 2 November 2026. The digit mass was 1.0000 in every reading, and the most likely token was always a digit. Cost about $0.63, start-up and download included.

## Result

| arm | g [95 % CI] | ĉ [95 % CI] | R² / leave-one-out | mean Δ [95 % CI] | slope vs. permutation null | moving items toward ĉ |
|---|---|---|---|---|---|---|
| critical | 0.653 [0.522, 0.769] | 1.884 [1.657, 2.118] | 0.750 / 0.718 | −0.443 [−0.705, −0.194] | p = 2.5 × 10⁻⁵ | 24 / 30 (p = 0.011) |
| praise | 0.739 [0.622, 0.859] | 2.990 [2.876, 3.109] | 0.884 / 0.863 | +0.273 [−0.027, +0.565] | p = 2.5 × 10⁻⁵ | 30 / 30 (p = 2.5 × 10⁻⁵) |

Preregistered criteria: **C1 (attraction) and C2 (two destinations) hold, at full scale**, so outcome A. The C2 margin is 2.876 − 2.118 = **0.758**. Targets 1.107 apart, arm-swap p = 1.0 × 10⁻⁴; shared g = 0.700 [0.608, 0.792]. Full output: [`R1b_output_items30_K10.txt`](R1b_output_items30_K10.txt).

**Reading.**
- On every released response, an open-weights judge of another family, ten times larger than R1a's, finds the attraction and the two destinations that the original judge found.
- The gains are 0.65 (critical) and 0.74 (praise); campaign 1 had 0.72 and 0.68, R1a 0.74 and 0.73.
- The targets, 1.88 and 2.99, lie closer to campaign 1's (1.46 and 2.94) than R1a's 7B reader did (2.35 and 3.34). Amplitude agreement across readers was not a criterion (§0).
- With R1a, the "single judge family" limit recedes for these two readers: a 7B reader on a reduced sample, and a 72B reader on all responses.

## Argmax reading (secondary)

The preregistration (§3 R1) makes r the primary reading and asks for the argmax to be reported. Here are the same 1 200 readings, with the most likely digit in place of r ([`R1b_argmax_input_items30_K10.json`](R1b_argmax_input_items30_K10.json)):

| arm | g [95 % CI] | ĉ [95 % CI] | R² / leave-one-out | mean Δ [95 % CI] |
|---|---|---|---|---|
| critical | 0.638 [0.494, 0.758] | 1.864 [1.622, 2.115] | 0.726 / 0.689 | −0.427 [−0.690, −0.177] |
| praise | 0.738 [0.627, 0.854] | 2.994 [2.880, 3.117] | 0.889 / 0.869 | +0.283 [−0.023, +0.580] |

**C1 and C2 hold on the argmax as on r**; the C2 margin is 2.880 − 2.115 = 0.765. In 877 of the 1 200 readings the most likely digit carries more than 90 % of the mass, and r differs from the argmax by 0.08 on average. In 8 readings the two most likely digits tie exactly, and the argmax then takes the lower one. The input was built from the raw readings, then rebuilt independently from the same raw file by a fresh instance, which obtained identical arms and an identical analysis. `check_results.py` reruns it. Full output: [`R1b_argmax_output_items30_K10.txt`](R1b_argmax_output_items30_K10.txt).

## Verification

- **Reproduce the analysis:** `python3 -I code/check_results.py` reruns the frozen analysis on [`R1b_input_items30_K10.json`](R1b_input_items30_K10.json) and compares the result with the published output. CI runs it on every push.
- **Independent recomputation before publication:** a fresh instance worked from the raw files only.
  - Verdict: **conforming with reservations**. Report SHA-256 `e2a9b3f4545f1b28c88a1bc84e10c59902ffa3e629b359c0e37d2d0230677ed0`, private, because it contains the judge prompt.
  - What it checked: the machine's inputs and the logged revision; 1 200 unique readings with none missing; the prompts rendered exactly as in R1a, with prompt and response hashes rebuilt for 1 200 of 1 200, and the 360 readings shared with R1a carry the same prompts; digit mass at least 0.9999997, with a digit always on top; the analysis input rebuilt exactly and the output reproduced byte for byte; the run cost, $0.177 from launch to end, under its $0.82 cap.
  - Its reservations, all minor and without effect on the readings or the analysis:
    - two guards of R1a's script were not carried over, distinct digit token ids and a prompt shorter than the context; the ids 16–20 are distinct and the longest prompt has 500 tokens;
    - the script headers still say "2 400", the error the erratum corrects, while the code reads the 600 lines of each file;
    - it checked the prompts with the 7B tokenizer, not the 72B revision's;
    - the push of the raw files cannot be verified offline.
- **Kept but not released,** identified by SHA-256:
  - readings: `1470a455a58d7bc6ea52fe1e8c73d5b48320b7c69da98b8f28fd38891d1d68f5`
  - analysis input: `2dd4b3a9f013691a…`
  - analysis output: `32c22b53b9fbf9a8…`
  - report: `5597b95474a9bca3…`
  - all in a private repository at commit `b5988e5`.
