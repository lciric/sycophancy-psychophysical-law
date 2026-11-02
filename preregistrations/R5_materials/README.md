# R5 materials — human readers, fixed before any human data

**Dated 2 November 2026.** This note completes §3 R5 of the preregistration [`2026-11-02_follow-up_runs_R1-R5.md`](../2026-11-02_follow-up_runs_R1-R5.md) (SHA-256 `a2f7e2f4…`, Zenodo [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831)) with the materials and the frozen analysis. It is archived with the release that contains it, before the study is published on Prolific. Nothing in §3 R5 changes.

## Stimuli

- **The 240 released responses** that §3 R5 names: the 30 items × {neutral, pressured} × the two arms × k ∈ {0, 1}, taken verbatim from [`data/c2a_generations.json`](../../data/c2a_generations.json) and [`data/c2b_generations.json`](../../data/c2b_generations.json). Readers see the response only, as the judge did; they never see the item, the arm, the condition or k.
- The responses are shown as they are. Some pressured responses mention the user's opinion ("I'm glad you think…"); the judge saw the same text, and it is not edited.
- **Two attention checks** with unambiguous polarity, written now: `ATT_NEG` (a clearly negative assessment; passes at 1 or 2) and `ATT_POS` (a clearly positive one; passes at 4 or 5). Their texts are in the CSV files.
- [`R5_stimuli.csv`](R5_stimuli.csv) holds the 242 rows, one per stimulus. [`R5_groups.csv`](R5_groups.csv) holds 30 reader sessions of 42 rows: 40 responses and the 2 checks, shuffled. Over the 30 sessions each response appears exactly 5 times, never twice in one session. Columns starting with `META_` are hidden from participants by Prolific's AI Task Builder. Both files are rebuilt byte for byte by [`code/make_r5_stimuli.py`](../../code/make_r5_stimuli.py) (`--check`) from the released data, seed 20261105.

## Readers and instruction

- Five readers per response, fluent in English, recruited on Prolific. One reader takes one session.
- **Instruction:** the scale and wording of the judge prompt (SHA-256 `6c95c1c0…`), as §3 R5 says. The judge prompt is not public; the participants will read its wording. The exact instruction text is fixed before the study opens, and its SHA-256 is recorded in a dated note in this folder.
- Payment at Prolific's recommended rate (£9 per hour or more).

## Exclusion and replacement

- A reader who fails either attention check is excluded, with all their ratings (§3 R5).
- An excluded reader's session is offered again to a new reader, once, before any analysis. The analysis then uses every valid reader; the number of valid readers per response is reported.

## Analysis, frozen now

[`code/analyse_humans.py`](../../code/analyse_humans.py) takes the Prolific export reduced to three columns (`participant_id`, `id`, `rating`) and computes:
- per response, the mean over its valid readers;
- per item, arm and condition, the K = 2 values (k = 0, 1), analysed by [`code/analyse_runs.py`](../../code/analyse_runs.py): **C1**, **C2** and the regime;
- **C5:** per arm, Spearman's ρ between the human item displacements and the campaign-1 judge's item displacements on the same responses, with a 95 % item-bootstrap interval (B = 10 000, seed 20261105); C5 holds if the interval excludes 0 in both arms.

Outcome A: C1, C2 and C5 hold — human readers see the attraction and the judge tracks them. Outcome B: any fails. Its self-test runs on simulated readers.

## Pilot with acquaintance readers

A pilot that borrows these materials with readers the author knows is declared, before any reading, in [`2026-11-02_note_R5_pilot_acquaintances.md`](2026-11-02_note_R5_pilot_acquaintances.md). It is reported as **R5-pilot**, never as R5.
