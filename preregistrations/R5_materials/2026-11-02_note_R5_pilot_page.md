# Dated note — R5-pilot: the readers' page and its instruction, fixed before the first reading

**Dated 2 November 2026, 17:35 Paris (16:35 UTC). Written before any reading of the pilot.** This is the second dated note announced in [`2026-11-02_note_R5_pilot_acquaintances.md`](2026-11-02_note_R5_pilot_acquaintances.md). It records the instruction and the page that the readers of **R5-pilot** use, before anyone reads.

## The instruction

- On 2 November 2026 the author decided that the readers of the pilot see the scale and wording of the judge prompt (SHA-256 `6c95c1c0…`), as §3 R5 says.
- The instruction is that prompt, word for word, except for three edits. The edits were specified before the instruction was drawn from the prompt, and nothing else was changed:
  - (a) The slot where the response was inserted is removed, with its label and the blank line before it. The reader sees the response on its own, below the instruction.
  - (b) The sentence telling the model how to format its output is replaced by "Choose one number from 1 to 5."
  - (c) Words addressing the model as "you" would have been adapted for a human reader. The prompt has none, so nothing changed.
- The question under each response is the prompt's own sentence asking for the rating. The labels of 1 and 5 are the prompt's words.
- The instruction file has four keys: instruction, question, label_low and label_high. Its SHA-256 is `f88065918ae6e3fecf86dedcbabe8e6d78d3919e35727f1fcae5fe26323fd1a1`. Like the judge prompt, it is not public.

## The page

- The page given to readers is built by `python3 -I code/make_r5_page.py --instruction <instruction file> <page>` at the commit that adds this note. Its SHA-256 is **`5eb12be25a6704bea790d410290d2628b4cd46a90a87f1a9e9d1d5b9004b6d02`**.
- It differs from the public template [`pilot/reading_page_template.html`](pilot/reading_page_template.html) (SHA-256 `0f80935ac443ba73e4fe73c926026855f0fe1d9cef454b720840eb19acb5145c`) by one line only: the instruction. This is what the first note says.
- **One display change since the first note, made before any reading.** The instruction now stands above every response, as it stood above every response for the judge. Its wording and its five scale labels are therefore in view at each rating, and the instructions screen says so. Nothing else changed: the order of the texts, the reader and session codes, the absence of a way back and the returned CSV are as in the first note.
- The page was tested end to end in a headless browser at phone size: 42 ratings in, 43 CSV lines out (header included), progress kept across a reload, no script error.

## What does not change

The following are those of the first note:
- the readers;
- the fixed sentence said to them;
- the assignment by rounds;
- the exclusion rule;
- the frozen analysis;
- the reporting under **R5-pilot**.
