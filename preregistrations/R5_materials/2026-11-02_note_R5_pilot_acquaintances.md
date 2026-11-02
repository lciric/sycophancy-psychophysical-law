# Dated note — R5-pilot: the R5 protocol with acquaintance readers, declared before any reading

**Dated 2 November 2026, afternoon. Written before any reading of the pilot, and archived on Zenodo with the release that contains it.** This note declares a pilot that is **not R5**. The preregistration ([`2026-11-02_follow-up_runs_R1-R5.md`](../2026-11-02_follow-up_runs_R1-R5.md) §3 R5) ties R5 to a Prolific study, with readers who do not know the author. That run stays registered, unchanged, and keeps its name. The pilot below borrows its materials and its analysis, changes who reads, and is reported under its own name, **R5-pilot**, never pooled with R5.

## What is the same as R5

- The 240 released responses and the two attention checks, in the 30 reading sessions of [`R5_groups.csv`](R5_groups.csv): 40 responses and 2 checks per session, each response in 5 sessions.
- The instruction: the scale and wording of the judge prompt (SHA-256 `6c95c1c0…`), as §3 R5 says.
- The exclusion rule: a reader who fails an attention check is excluded with all their ratings.
- The frozen analysis [`code/analyse_humans.py`](../../code/analyse_humans.py), run with `--label R5-pilot`: C1, C2 and the regime through `analyse_runs.py`, and C5, Spearman's ρ between human and judge item displacements. Outcome A: C1, C2 and C5 hold; outcome B: any fails.

## What differs, declared

- **Readers:** acquaintances of the author, fluent in English, unpaid. This is the main limitation: readers who know the author could guess what he hopes to see. Two guards follow.
- **What readers are told** is fixed now, and nothing more is said, in writing or aloud: *"I am collecting human readings of short texts written by an AI model. Each text is an assessment of another text. You will read them one at a time and give each a number from 1 to 5, following the instruction on the page. It takes about 35 minutes per session. I cannot tell you more about the study until you have finished."* For French-speaking readers, its faithful translation, also fixed now: *« Je rassemble des lectures humaines de courts textes écrits par un modèle d'IA. Chaque texte est une évaluation d'un autre texte. Tu les liras un par un et tu donneras à chacun un nombre de 1 à 5, en suivant la consigne de la page. Une session prend environ 35 minutes. Je ne peux pas t'en dire plus sur l'étude avant que tu aies fini. »* Readers are not told about pressure, praise, criticism, flattery, sycophancy, a fixed point or the hypothesis, nor which texts come from which condition. The response texts themselves sometimes mention the user's opinion; readers see them as the judge did.
- **Several sessions per reader:** a reader may take up to six sessions, all from the same round. Sessions G00–G05 form round 0, G06–G11 round 1, and so on to G24–G29; within a round no response appears twice, so no reader sees a response twice. The analysis stops if one does.
- **Assignment:** reader codes P01, P02, … are given in the order readers agree, and each reader receives the sessions of one round, round 0 first, filling a round before opening the next. Excluded readers' sessions are offered once to new readers before the analysis.
- **Page:** readers use a self-contained web page, one response at a time, with no way back to a previous response; it works offline and sends nothing. They return their ratings as text or as a file. The page is built by [`code/make_r5_page.py`](../../code/make_r5_page.py); the public template is [`pilot/reading_page_template.html`](pilot/reading_page_template.html). The copy given to readers differs from it only by the instruction text, which is not public; its SHA-256 is recorded in a second dated note before the first reading.
- **Display:** responses are shown verbatim, including the end-of-turn marker `<|eot_id|>` that ends 239 of the 240, as the judge read them; the page tells readers to ignore it.

## How it is reported

As **R5-pilot (acquaintance readers)**, in its own folder, with this note linked, the number of readers and of exclusions, and the limitation above stated first. A positive result means human readers who know the author read the attraction as the judge did; it does not replace R5.
