# R4: sixty new items, zero free parameters

Preregistered in [`preregistrations/2026-11-02_follow-up_runs_R1-R5.md`](../../preregistrations/2026-11-02_follow-up_runs_R1-R5.md) §3 R4. Archived on Zenodo before any data: [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831). The run targets one limit of campaign 1: its 30 items.

**What was run.**
- **Items.** A fresh model instance wrote 60 one-sentence evaluative claims from the brief [`preregistrations/R4_brief.txt`](../../preregistrations/R4_brief.txt) alone. They were committed to this repository in [`R4_items.txt`](../../preregistrations/R4_items.txt) at 00:11 UTC on 2 November 2026, before any generation (provenance: [`R4_items_provenance.md`](../../preregistrations/R4_items_provenance.md)).
- **Generation.** Llama-3.1-8B-Instruct (fp32, TransformerLens 2.17.0) received the campaign-1 elicitation in three conditions: neutral, critical, praise. K = 5 per item and condition, with seeds 6 000 000 + 100·i + k shared across the three conditions of each (i, k). Sampling used the campaign-1 loop at T = 0.3, with at most 400 new tokens, through a key–value cache. On 20 out-of-family seeds, the cache and the plain loop gave 20 identical sequences out of 20. The cache is still declared as a deviation.
- **Judging.** 900 generations, 07:57–10:02 UTC, then judged by `claude-opus-4-6` at temperature 0 with the campaign-1 prompt, reading each response in full. The 900 calls returned one digit each.

## Result

**Out of sample, with the campaign-1 law and no refit** (critical g = 0.7177, ĉ = 1.4557; praise g = 0.6778, ĉ = 2.9369):

| arm | R² of the law | R² of a constant shift | SSE(shift) − SSE(law) [95 % CI] | moving items toward the campaign-1 target |
|---|---|---|---|---|
| critical | **0.683** | −0.280 | +72.6 [45.2, 101.9] | p = 2.5 × 10⁻⁵ |
| praise | **0.579** | −0.013 | +30.2 [14.1, 47.4] | p = 7.5 × 10⁻⁵ |

**Free fit on the new items:**

| arm | g [95 % CI] | ĉ [95 % CI] | R² / leave-one-out | mean Δ [95 % CI] |
|---|---|---|---|---|
| critical | 0.821 [0.713, 0.923] | 1.333 [1.116, 1.548] | 0.748 / 0.733 | −1.350 [−1.637, −1.067] |
| praise | 0.617 [0.499, 0.738] | 3.225 [2.995, 3.513] | 0.624 / 0.598 | +0.153 [−0.073, +0.387] |

**Preregistered criteria: C1, C2, C3 and C4 all hold**, so outcome A. The C2 margin is 1.448, and the targets lie 1.892 apart (arm-swap p = 1.0 × 10⁻⁴). Full output: [`R4_output_items60.txt`](R4_output_items60.txt).

**Reading.**
- On 60 items nobody had seen when the law was fitted, the campaign-1 law predicts about two thirds (criticism) and three fifths (praise) of the displacement without any refitted parameter.
- A constant shift does worse than predicting no change at all.
- Refitted on the new items, the targets are close to campaign 1's (1.33 and 3.23, against 1.46 and 2.94).
- The counter-intuitive prediction of the law held out of sample: 25 of the 60 new items sit above the praise target, and under praise they moved *down*, by −0.60 on average (intra-item permutation p = 2.5 × 10⁻⁵; `descent_above_target` in the output). A directional push cannot produce this.

## Refusals

9 of the 900 responses are refusals ("I can't provide a subjective evaluation…"). All 9 are under praise, on items 40 (4 of 5), 37 (2 of 5), 18, 45 and 55, and the judge rated each of them 3. The released campaign-1 data contain 85 refusal-like responses in 1 200. Neither campaign 1 nor the preregistration excludes refusals, so they are kept, as there.

A rating of 3 lies close to the praise target (3.2), so a refusal can look like attraction. A post hoc, descriptive sensitivity was therefore fixed before its result was seen. The preregistered verdict remains the full run's.
- (a), removing only the 9 refusals, is not computable under the frozen code, which requires the same K for every item (`load` in [`code/analyse_runs.py`](../../code/analyse_runs.py)). It was replaced, before any variant was seen, by (c).
- (b) removes items 37 and 40 whole.
- (c) removes whole the five items with a refusal (18, 37, 40, 45, 55), hence every refusal.

| variant | items | g critical / praise | ĉ critical / praise | C2 margin | R² of the law out of sample (critical / praise) | praise: SSE(shift) − SSE(law) [95 % CI] | C1–C4 |
|---|---|---|---|---|---|---|---|
| full run | 60 | 0.821 / 0.617 | 1.333 / 3.225 | 1.448 | 0.683 / 0.579 | +30.2 [14.1, 47.4] | all hold |
| (b) without 37 and 40 | 58 | 0.815 / 0.606 | 1.330 / 3.230 | 1.427 | 0.678 / 0.560 | +27.8 [12.0, 45.3] | all hold |
| (c) without 18, 37, 40, 45, 55 | 55 | 0.817 / 0.592 | 1.345 / 3.273 | 1.445 | 0.677 / 0.534 | +24.2 [8.5, 40.6] | all hold |

**The refusals do not carry outcome A**: all four criteria hold without them, and the praise gain barely moves.
- Inputs: [`R4_sensitivity_refusals-b_input_items58.json`](R4_sensitivity_refusals-b_input_items58.json) and [`R4_sensitivity_refusals-c_input_items55.json`](R4_sensitivity_refusals-c_input_items55.json). Each is the run's input with whole items removed, nothing else changed. Each output sits beside its input.
- Independent recomputation before publication: a fresh instance found each input identical to the run's except for the announced items, in both arms. It recounted 9 refusals, all under praise, reproduced both outputs byte for byte, and confirmed that the frozen code rejects (a). Verdict **conforming**; report SHA-256 `f29c3d6bcfa2485d235d550d203e068ebdfcce98d1eb49333b6131ff5bb8216c`, private.

## Verification

- **Reproduce the analysis:** `python3 -I code/check_results.py` reruns the frozen analysis, with the out-of-sample criteria, on [`R4_input_items60.json`](R4_input_items60.json) and on both sensitivity inputs. It compares each result with the published output, and CI runs it on every push.
- **Independent recomputation before publication:** a fresh instance worked from the raw files only.
  - Verdict: **conforming with reservations**. Report SHA-256 `ede071b56649bbc4f25e11aed62bb8af0addc1f39430bd9d1257c0f286c98825`, private.
  - What it checked: items identical to `7ccb3ec`, the plan, the prompts, the trial runs, and the 900 judge prompts and responses by hash. It rebuilt the analysis input and replayed the analysis byte for byte.
  - Reservation 1: the Hugging Face revision of the model was not logged. It is inferred from the public API: `main` at `0e9e39f2…`, unchanged since 2024-09-25.
  - Reservation 2: generation took longer than projected and passed the original cost cap before an amendment that counts the judge. The total cost, $2.39 for GPU and judge, is under the amended cap of $3.90.
- **Kept but not released,** identified by SHA-256:
  - generations: `5d54c9b35f7d17da943bd389144aa7a3ebfef77f705744d221665a38c2e9130d`
  - judgments: `a4ae0782ec1a5790f6c46ea00898029205c4a508427fa1c7b2141241f4a3d3b6`
  - analysis input: `4f62d51783d7fbb1…`
  - analysis output: `be92fa34b37351eb…`
  - all in a private repository at commit `12d3444`; the refusal sensitivity at commit `c930026`.
