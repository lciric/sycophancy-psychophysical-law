# Follow-up runs — status

**Updated 2 November 2026, 12:13 Paris (11:13 UTC).** This file says what has been run, what is running, and what comes next. Every result enters [`results/`](results/) only after an independent recomputation from its raw files. Raw files that contain item texts stay private and are identified by SHA-256.

**Fixed before any data.** The preregistration [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](preregistrations/2026-11-02_follow-up_runs_R1-R5.md) was archived on Zenodo before the first token: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831), 1 November 2026, 23:03 UTC. The frozen analysis is [`code/analyse_runs.py`](code/analyse_runs.py). The 60 R4 items were committed before any R4 generation, in `7ccb3ec`, 00:11 UTC.

## Done

| run | limit addressed | result |
|---|---|---|
| **R2**: the model's own rating, no judge | the judge | C1 and C2 hold on the run (outcome A). Criticism: g = 0.63, R² = 0.91. Praise: g = 0.14 [0.03, 0.24]. C2 does not survive a change of llama.cpp implementation (independently re-checked). See [`results/R2/`](results/R2/README.md). |
| **R1a**: open-weights judge (Qwen2.5-7B) on the released responses, 360 readings | the judge | C1 and C2 hold (outcome A), with a C2 margin of 0.53. Gains 0.74 and 0.73, against 0.72 and 0.68 with the original judge. See [`results/R1a/`](results/R1a/README.md). |
| **R1b**: open-weights judge (Qwen2.5-72B) on all 1 200 released responses | the judge | C1 and C2 hold at full scale (outcome A), with a C2 margin of 0.76. Gains 0.65 and 0.74. The argmax reading agrees. See [`results/R1b/`](results/R1b/README.md). |
| **R3**: Qwen2.5-7B, Mistral-7B-v0.3 and Gemma-2-9B, 40 items × 3 conditions × K = 10 | one model | All three fail C1 and C2 (regime offset). Qwen and Mistral shift every item by about the same amount; for Qwen this is the preregistered outcome A. Gemma shows a strong attraction under criticism only (g = 0.93). See [`results/R3/`](results/R3/README.md). |
| **R4**: 60 new items written blind, committed before any generation | 30 items | C1–C4 hold (outcome A). The campaign-1 law with no refit explains R² = 0.68 (critical) and 0.58 (praise), against −0.28 and −0.01 for a constant shift. Without the items with refusals, all four criteria still hold. See [`results/R4/`](results/R4/README.md). |

## Running (times are Paris, 2 November)

Nothing is running. Every run that the 13:00 window allowed is done. R5 and the R3 secondary reading remain registered unchanged (see Later).

**R6, preregistered on 2 November in the afternoon** ([`preregistrations/2026-11-02_addendum_R6_dose_response.md`](preregistrations/2026-11-02_addendum_R6_dose_response.md)): three intensities of the pressure sentence on the four families, 30 items, K = 5, analysed by the frozen [`code/analyse_dose.py`](code/analyse_dose.py). It starts only after the addendum is archived on Zenodo and a budget is signed.

The preregistration fixes what each outcome means (two outcomes per run, written in advance).

## Declared deviations and precisions, all fixed before the data they touch

- **Quantisation in R1a and R2.** Q4_K_M on CPU, declared in the preregistration. R2 uses one BOS, the literal Llama-3.1 template; campaign 1 had two. R1a keeps Qwen's default system message, the literal "Qwen chat template".
- **Generation.** R3 and R4 run the frozen campaign-1 sampling loop with a key–value cache ("route B"). On 20 out-of-family seeds per model, routes A and B gave 20 identical sequences out of 20. It is still declared as a deviation. Weights are fp32, as in campaign 1.
- **Mistral-7B-v0.3** is loaded through TransformerLens's v0.1 converter. Its log-probabilities match transformers within 5 × 10⁻⁵, the same order as Qwen and Llama.
- **Gemma-2-9B.** TransformerLens and transformers (sdpa attention) differ by up to 0.39 in log-probability. The likely cause is attention soft-capping, which sdpa does not apply. The rule was fixed before any Gemma output. Gemma counts as a primary R3 family if TransformerLens matches transformers with eager attention within 10⁻³. Otherwise it is reported as secondary, outside the R3 conclusion. **Result of the check:** the largest difference with eager attention is 6.7 × 10⁻⁵ (top-1 token identical at 38 positions out of 38), so Gemma is a primary family. With sdpa it stays 0.39, which confirms the cause.
- **Judge.** `claude-opus-4-6`, temperature 0, the campaign-1 prompt. It reads every response in full: campaign-1 code truncated at 2,000 characters, but no campaign-1 response reached that length, so this matches what that judge actually read.
- **Clocks.** One machine's clock runs at least 12 minutes fast, so the order of events is taken from GitHub push times.

## Incidents, none of which reached an analysed number

- **R2, first attempt.** After a library change it read flat logits. It was rejected on that instrument ground alone, kept on file, and R2 was rerun from zero.
- **Import failure.** Four GPU machines failed at import before loading any model. They were replaced, at about $0.27.
- **Frozen machine.** One Mistral machine froze. Its 50 generations were saved, and the run resumed without repeating any.
- **Private deposit.** A `.gitignore` rule silently dropped four files from a private deposit. This was caught by checking the commit against its own hash list, and fixed by a new commit, with no history rewrite.

## Next, today

1. Run R6 once its addendum is archived and its budget signed; then an independent recomputation, then `results/R6/`.
2. Register the preregistration on OSF as well, mirroring the Zenodo archive.

## Later (planned)

- **R5:** human readers on 240 released responses, as preregistered.
- **R2 at full precision** (transformers, bf16/fp32). This removes the quantisation deviation and the sensitivity to the llama.cpp implementation. Add more readings per item on the praise arm.
- **R3 secondary reading:** the R1a reader (Qwen2.5-7B, CPU) on the R3 responses, as preregistered. It did not fit before 13:00 Paris and remains registered unchanged.
- **Manuscript:** cite the numbers of `code/reproduce.py`, and state that the third rival is excluded by magnitude, not by the count of descents.
