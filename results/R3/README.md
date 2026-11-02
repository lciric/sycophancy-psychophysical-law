# R3: three model families at K = 10

Preregistered in [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](../../preregistrations/2026-11-02_follow-up_runs_R1-R5.md) §3 R3. Archived on Zenodo before any data: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831). The run targets one limit of campaign 1: a single model.

**What was run.**
- **Models:** Qwen2.5-7B-Instruct (m = 0), Mistral-7B-Instruct-v0.3 (m = 1), Gemma-2-9B-it (m = 2).
- **Design:** items 0–39 of the campaign-1 corpus (not released); neutral, critical, praise; K = 10. The seed 5 000 000 + 100 000·m + 100·i + k is shared by the neutral and pressured generations of each (i, k).
- **Elicitation:** the campaign-1 instruction and suffixes (not released), in each model's own chat template. T = 0.3, top_p 1, top_k 0, at most 400 new tokens.
- **Generation:** TransformerLens 2.17.0 in float32, with the campaign-1 sampling loop run through a key–value cache. On 20 out-of-family seeds per model, the cache and the plain loop gave 20 identical sequences out of 20. The cache is still declared as a deviation.
- **Judge:** `claude-opus-4-6`, temperature 0, the campaign-1 prompt (SHA-256 `6c95c1c0…`, not released), reading each response in full. 1 200 calls per model.
- **What the preregistration asks:** for each model, C1, C2 and the regime. It fixes an outcome only for Qwen, from an earlier run at K = 3: **A**, offset at K = 10; **B**, attraction.

## Result

| model | arm | g [95 % CI] | ĉ [95 % CI] | R² | mean Δ [95 % CI] |
|---|---|---|---|---|---|
| Qwen2.5-7B | critical | 0.118 [−0.068, 0.293] | −2.745 [−51.1, 54.3] | 0.041 | −0.685 [−0.812, −0.558] |
|  | praise | 0.274 [0.078, 0.495] | 1.999 [0.339, 2.450] | 0.157 | −0.290 [−0.443, −0.140] |
| Mistral-7B-v0.3 | critical | 0.187 [−0.016, 0.434] | −0.688 [−27.6, 19.9] | 0.049 | −0.680 [−0.815, −0.552] |
|  | praise | 0.333 [0.074, 0.572] | 5.941 [4.651, 13.200] | 0.118 | +0.997 [+0.845, +1.145] |
| Gemma-2-9B | critical | 0.925 [0.835, 1.011] | 1.095 [0.967, 1.226] | 0.913 | −1.195 [−1.407, −0.980] |
|  | praise | 0.207 [−0.013, 0.456] | 3.535 [−1.288, 9.893] | 0.086 | +0.237 [+0.083, +0.395] |

For comparison, campaign 1 found for Llama-3.1-8B-Instruct g = 0.72 and ĉ = 1.46 under criticism, g = 0.68 and ĉ = 2.94 under praise.

**Qwen2.5-7B: C1 fails, C2 fails, regime offset, so outcome A.** The non-transfer predicted by the earlier K = 3 run holds at full precision. C1 fails through the critical arm alone. Under praise the gain excludes 0, with a target near 2, and Qwen moves *down* on average (Δ = −0.29).

**Mistral-7B-v0.3: C1 fails, narrowly, C2 fails, regime offset.** The lower bound of the critical gain is −0.016. The preregistration fixes no outcome for Mistral. Both arms move clearly, but the move barely depends on the neutral rating (R² 0.05 and 0.12): a shift, not an attraction. Under praise Mistral moves *up* by about one point (Δ = +1.00), the opposite of Qwen.

Under criticism, for Qwen and Mistral, the slope does not beat the within-item permutation null (p = 0.28 and 0.25), and the law predicts held-out items worse than their mean (leave-one-out R² −0.06 and −0.04).

**Gemma-2-9B: C1 fails, narrowly, C2 fails, regime offset.** The lower bound of the praise gain is −0.013. The preregistration fixes no outcome for Gemma. Its two arms differ sharply:
- **Under criticism**, Gemma carries almost every item to the bottom of the scale: g = 0.93 [0.84, 1.01], ĉ = 1.10, R² = 0.91. That is a stronger gain and a lower target than Llama's, and the interval of g reaches 1: a nearly complete capture.
- **Under praise**, it moves up a little (Δ = +0.24), with a small gain whose interval just reaches 0 (g = 0.21 [−0.01, 0.46], R² 0.09).

Full outputs: [`R3_qwen_output_items40_K10.txt`](R3_qwen_output_items40_K10.txt), [`R3_mistral_output_items40_K10.txt`](R3_mistral_output_items40_K10.txt), [`R3_gemma_output_items40_K10.txt`](R3_gemma_output_items40_K10.txt).

**Reading.**
- Attraction under both pressures, as found for Llama-3.1-8B, transfers to none of the three families.
- Qwen2.5-7B and Mistral-7B-v0.3 shift every item by about the same amount instead of drawing them toward a fixed point.
- Gemma-2-9B shows the attraction under criticism only, and strongly.
- Under praise the direction depends on the model: up for Mistral and Gemma, down for Qwen.

## Declared deviations

- **Secondary reading not run.** The preregistration also asks for the R1a reader on the same responses. 3 600 readings at about 6 s each on CPU did not fit before 13:00 Paris. It remains registered unchanged (§4), and no partial reading was made.
- **Model revisions not logged** at download, contrary to "revisions pinned at download"; R4 has the same gap. They are inferred from the public Hugging Face API, whose main branches have not moved since before the run: Qwen2.5-7B-Instruct `a09a3545…` (last change 2025-01-12), Mistral-7B-Instruct-v0.3 `c170c708…` (2025-12-03), gemma-2-9b-it `11c9b309…` (2024-08-27).
- **Mistral loading.** TransformerLens 2.17.0 does not list v0.3; it was loaded through the v0.1 converter with the v0.3 name added. Its log-probabilities match transformers within 5 × 10⁻⁵. Two BOS tokens open Mistral's and Gemma's prompts, as two opened Llama's in campaign 1.
- **Mistral machines.** One machine froze after 50 generations. The run resumed on a new machine without repeating any (item, k, condition), and a further machine ran items 20–39. The union holds 1 200 unique generations.
- **Gemma resolution check.** Before any Gemma output was read, TransformerLens and transformers (sdpa attention) differed by up to 0.39 in log-probability. The rule fixed then: Gemma is a primary family if TransformerLens matches transformers with eager attention within 10⁻³. The result was 6.7 × 10⁻⁵, with the top-1 token identical at 38 positions out of 38, so Gemma is primary. The sdpa gap comes from Gemma 2's attention soft-capping, which sdpa does not apply.
- **Gemma machines.** Items 0–32 come from one machine and items 33–39 from a second, by a union rule fixed before any reading. Ten generations of the first machine on item 33 lie outside the union and were never judged. The union, rebuilt independently, holds 1 200 unique generations. The ten item-33 generations that both machines made, with the same seeds, are identical, 10 out of 10: the two machines reproduce each other.
- **Long responses and duplicates.** Qwen: one response reached 400 tokens, kept and counted; three exceed 2 000 characters. Mistral: one reached 400 tokens; one exceeds 2 000 characters. Gemma: none reached 400 tokens or 2 000 characters. The judge read every response in full. No model produced a refusal. Gemma gave 5 exact duplicates, each within one item and condition from different seeds: short responses at T = 0.3. Qwen and Mistral gave none.

## Verification

- **Reproduce the analysis:** `python3 -I code/check_results.py` reruns the frozen analysis on [`R3_qwen_input_items40_K10.json`](R3_qwen_input_items40_K10.json), [`R3_mistral_input_items40_K10.json`](R3_mistral_input_items40_K10.json) and [`R3_gemma_input_items40_K10.json`](R3_gemma_input_items40_K10.json). It compares each result with the published output, and CI runs it on every push.
- **Independent recomputation before publication:** for each model, a fresh instance worked from the raw files only.
  - **Qwen: conforming.** Report SHA-256 `f29c3d6bcfa2485d235d550d203e068ebdfcce98d1eb49333b6131ff5bb8216c`, private.
    - What it checked: the 40 items against the corpus; the plan, seeds, settings and cache route; the trial run; the judge cost. It rebuilt the 1 200 judge prompts from their SHA-256 with the full response; a cut at 2 000 characters would give back only 1 197 of them. It rebuilt the analysis input identically and reproduced the output byte for byte.
    - Reservations: the corpus is not in the public `data/`, which publishes only its hash, so the items were checked on a local copy carrying that hash; the campaign-1 instruction is not released and was checked through an indirect witness; the machine's clock ran 10 to 13 minutes fast.
  - **Mistral: conforming with reservations.** Report SHA-256 `636ae02b93919afffecb9ddbec1a50c613e4446c987ed4776689ef6313f785a6`, private.
    - What it checked, all conforming: both item slices against the corpus. The union is exactly the first machine's file followed by the second's: 1 200 unique (item, k, condition), none repeated by the resumption. Seeds, cache route and settings; Mistral's chat template byte for byte; A/B 20 of 20 and log-probabilities within 5 × 10⁻⁵; the same software on every machine apart from the NVIDIA driver. The 1 200 judge prompts and responses rebuilt from their SHA-256; the judge cost; the output reproduced byte for byte.
    - Reservations: the first machine's log was missing from the deposit (recovered from the branch history and deposited); the revision was not logged (see above); two BOS tokens and the added v0.3 name, both declared.
  - **Gemma: conforming with reservations.** Report SHA-256 `3e66012da0f77b1d0c0a00139ae514561bc0731403c2c84639d1bc4de7735d7f`, private.
    - What it checked: the union byte for byte (the first machine's 990 lines for items 0–32, then the second machine's 210), 1 200 unique (item, k, condition), seeds and cache route, and the 10 excluded lines, all on item 33. It recounted 5 exact duplicates, no response at 400 tokens or beyond 2 000 characters, and no refusal. It rebuilt the 1 200 judge prompts and responses from their SHA-256 and recomputed the judge cost. It rebuilt the analysis input identically and reproduced the output byte for byte.
    - Reservations: the resolution check ran on a third machine after the generations, with the same GPU model and software; the 10 item-33 generations that both generation machines made are identical, so these machines reproduce each other. Two BOS tokens open Gemma's prompts, declared as for Mistral.
- **Kept but not released,** identified by SHA-256:
  - Qwen: generations `756a69a8cfa2b0cd4e3ee7a931ae097b02fa1dd98314c095c76f24df0452c79b`, judgments `b597562901b4d3ffe61d977bc381886f7b42b4915e6a959db48ec6cabb996ed0`, analysis input `f6523b3800bd4f7a…`, output `202d785cdf3542ea…`;
  - Mistral: generations of both machines `d2bbaf198dcf56b6f854860f1bce58c2cb4ace65ab2fbd2692d10ee4bf6867f8`, judgments `4e4fa96b5ecde1a86aa7648b23fe0d9a001ff5756aec0d4930d696fcadadf8db`, analysis input `661a08fff50ff681…`, output `e582bd1170dbd25a…`;
  - Gemma: generations of both machines `332574c228787dce4e006bd0ea6a2065a39988235553a9a1a69f90e07a87601b`, judgments `4f90d6fcc65c1a00ce6351b1edbad6cad6c51b93a237c5a6b401de228f0bd64a`, analysis input `f6cc3e067ee8d812…`, output `2b658d8b3eac2cbb…`;
  - report `6d1b40e7b9ff4d1e…`; Qwen and Mistral in a private repository at commit `b5988e5`, Gemma at commit `d0d1353`.
