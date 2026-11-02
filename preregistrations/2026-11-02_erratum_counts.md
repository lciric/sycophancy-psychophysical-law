# Erratum to the follow-up preregistration: two counts in §3 R1

**Dated 2 November 2026, 10:35 Paris (09:35 UTC).** Written after the R1a run and before any R1a result was published. The preregistration [`2026-11-02_follow-up_runs_R1-R5.md`](2026-11-02_follow-up_runs_R1-R5.md) (SHA-256 `a2f7e2f4…`, archived on Zenodo, [10.5281/zenodo.23870831](https://doi.org/10.5281/zenodo.23870831)) stays as archived. This note corrects two numbers in it.

- **What is wrong.** §3 R1 speaks of "the 2 400 released responses" and of "(720 readings)" for the reduced sample. Both numbers are wrong by a factor of two. The two released files hold 600 responses each: `data/c2a_generations.json` `a7c85816…` and `data/c2b_generations.json` `ec2f7ca5…`, each with 30 items × 2 conditions × 10 generations. That makes **1 200** responses in all. The sample rule as written, "every item, condition and arm at k ∈ {0, 1, 2}", gives 30 × 2 × 2 × 3 = **360** readings.
- **What was run.** R1a followed the rule as written, not the wrong number. The timing trial averaged 5.70 s per reading, above the 5.0 s threshold, so the reduced sample applied: k ∈ {0, 1, 2}, 360 readings. For R1b, "all responses" means the 1 200 released responses.
- **What does not change.** No criterion, threshold, sample rule or exclusion rule is affected. The error lies in the arithmetic of the preregistration text, not in its execution.
- **How it was found.** The executor saw it when the R1a count stopped at 360 instead of 720.
