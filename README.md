# Sycophancy as Attraction Toward a Fixed Point — data and code

**Author:** Lazar Ciric · **Status:** manuscript in preparation (November 2026); this repository holds the data and the code behind the reported figures.

On Llama-3.1-8B-Instruct, a rating revised under an unargued expression of preference follows an attraction law, Δ = g·(ĉ − p₀): the rating closes a fixed fraction g of its distance to an arm-specific target ĉ (critical pressure vs. praise), rather than moving by a fixed amount in the direction of the pressure.

**Reproduce every figure below:** `python3 -I code/reproduce.py` (needs only `numpy`).

| figure | value | source file |
|---|---|---|
| gain g, per arm (critical / praise) | 0.718 / 0.678 — shared-gain fit 0.70 | `data/c2a_results.json`, `data/c2b_results.json` |
| targets ĉ (critical / praise), 1–5 scale | 1.46 / 2.94 | same |
| fit R² (critical / praise) | 0.77 / 0.79 | same |
| leave-one-item-out R² (critical / praise) | 0.74 / 0.75 | same |
| design, campaign 1 | 30 items × 10 generations per item and condition (1 200 generations per campaign) | `data/c2a_generations.json`, `data/c2b_generations.json` |
| campaign 2 (40 items: the 30 above + 10 new, K = 5), S0 stratum | g = 0.71 / 0.77, ĉ = 1.47 / 2.84, R² = 0.73 / 0.70 | `data/c2full_polarity_2026-08-02.json` |

Each result file records in its `meta` the SHA-256 of the preregistration, of the generation file it was judged from, the judge (`claude-opus-4-6`, t = 0) and the ordinal polarity prompt (sha256 `6c95c1c0…`). `SHA256SUMS` lists the hash of every file here. The item texts and the Qwen2.5-7B comparison data are not included in this release.

**License:** MIT for the code (`LICENSE`); CC BY 4.0 for the data files (`data/LICENSE`).
