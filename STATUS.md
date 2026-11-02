# Follow-up runs — status

**Updated 2 November 2026, 10:44 Paris (09:44 UTC).** This file says what has been run, what is running, and what comes next. Every result enters [`results/`](results/) only after an independent recomputation from its raw files. Raw files that contain item texts stay private and are identified by SHA-256.

**Fixed before any data.** The preregistration [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](preregistrations/2026-11-02_follow-up_runs_R1-R5.md) was archived on Zenodo before the first token: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831), 1 November 2026, 23:03 UTC. The frozen analysis is [`code/analyse_runs.py`](code/analyse_runs.py). The 60 R4 items were committed before any R4 generation, in `7ccb3ec`, 00:11 UTC.

## Done

| run | limit addressed | result |
|---|---|---|
| **R2**: the model's own rating, no judge | the judge | C1 and C2 hold on the run (outcome A). Criticism: g = 0.63, R² = 0.91. Praise: g = 0.14 [0.03, 0.24]. C2 does not survive a change of llama.cpp implementation (independently re-checked). See [`results/R2/`](results/R2/README.md). |
| **R1a**: open-weights judge (Qwen2.5-7B) on the released responses, 360 readings | the judge | C1 and C2 hold (outcome A), with a C2 margin of 0.53. Gains 0.74 and 0.73, against 0.72 and 0.68 with the original judge. See [`results/R1a/`](results/R1a/README.md). |

## Running (times are Paris, 2 November)

| run | what | state | expected |
|---|---|---|---|
| R4 | 60 new items × 3 conditions × K = 5, Llama-3.1-8B, campaign-1 law with no refit (criteria C3, C4) | 675 / 900 generations at 10:32 | judged and recomputed around 11:45 |
| R3 | Qwen2.5-7B, Mistral-7B-v0.3, Gemma-2-9B; 40 items × 3 conditions × K = 10 | at 10:32: Qwen 800, Mistral 650, Gemma 500 (of 1 200 each) | Qwen and Mistral around 12:00; Gemma (two machines) around 12:30 |
| R1b | Qwen2.5-72B (bf16) as judge on all 1 200 released responses | starting around 11:15 | after 12:15 |

The preregistration fixes what each outcome means (two outcomes per run, written in advance).

## Declared deviations and precisions, all fixed before the data they touch

- **Quantisation in R1a and R2.** Q4_K_M on CPU, declared in the preregistration. R2 uses one BOS, the literal Llama-3.1 template; campaign 1 had two. R1a keeps Qwen's default system message, the literal "Qwen chat template".
- **Generation.** R3 and R4 run the frozen campaign-1 sampling loop with a key–value cache ("route B"). On 20 out-of-family seeds per model, routes A and B gave 20 identical sequences out of 20. It is still declared as a deviation. Weights are fp32, as in campaign 1.
- **Mistral-7B-v0.3** is loaded through TransformerLens's v0.1 converter. Its log-probabilities match transformers within 5 × 10⁻⁵, the same order as Qwen and Llama.
- **Gemma-2-9B.** TransformerLens and transformers (sdpa attention) differ by up to 0.39 in log-probability. The likely cause is attention soft-capping, which sdpa does not apply. The rule was fixed before any Gemma output. Gemma counts as a primary R3 family if TransformerLens matches transformers with eager attention within 10⁻³. Otherwise it is reported as secondary, outside the R3 conclusion.
- **Judge.** `claude-opus-4-6`, temperature 0, the campaign-1 prompt. It reads every response in full: campaign-1 code truncated at 2,000 characters, but no campaign-1 response reached that length, so this matches what that judge actually read.
- **Clocks.** One machine's clock runs at least 12 minutes fast, so the order of events is taken from GitHub push times.

## Incidents, none of which reached an analysed number

- **R2, first attempt.** After a library change it read flat logits. It was rejected on that instrument ground alone, kept on file, and R2 was rerun from zero.
- **Import failure.** Four GPU machines failed at import before loading any model. They were replaced, at about $0.27.
- **Frozen machine.** One Mistral machine froze. Its 50 generations were saved, and the run resumed without repeating any.
- **Private deposit.** A `.gitignore` rule silently dropped four files from a private deposit. This was caught by checking the commit against its own hash list, and fixed by a new commit, with no history rewrite.

## Next, today

1. Judge R4 and R3 as their generations finish. Analyse with the frozen code. Run an independent recomputation, then publish here.
2. Run the Gemma resolution check (TransformerLens against transformers with eager attention) before any Gemma response is read.
3. Run R1b. Register the preregistration on OSF as well, mirroring the Zenodo archive.

## Later (planned)

- **R5:** human readers on 240 released responses, as preregistered.
- **R2 at full precision** (transformers, bf16/fp32). This removes the quantisation deviation and the sensitivity to the llama.cpp implementation. Add more readings per item on the praise arm.
- **Gemma at full agreement:** rerun if the resolution check classifies it as secondary.
- **Manuscript:** cite the numbers of `code/reproduce.py`, and state that the third rival is excluded by magnitude, not by the count of descents.
- **A graded-intensity (dose–response) extension** of the pressure manipulation, pending design decisions.
