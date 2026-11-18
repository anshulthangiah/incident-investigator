# Evaluation results: real-model baseline

One real model, run once on each of the 22 invented scenarios. Date: 2026-11-18.

## What this is and is not

- It is one baseline. One model (`claude-sonnet-5-5`, provider `anthropic`), one run per scenario, on the invented mock system.
- It is not an accuracy claim. 22 invented incidents, scored by coarse text checks, cannot tell you how the tool would do on any other system.
- It is not stable evidence. Scenarios that were run twice moved (see [Stability](#stability)).
- It says nothing about user value or time saved. No user was measured.

### A scoring change, disclosed

The scoring rule for required phrases (`must_mention`) was revised after the first round was seen. The first-round reports were then scored again offline with the new rule. No new model call was made for that. The change:

- A required phrase also matches a plain paraphrase (`PHRASE_ALTERNATIVES` in `evals/run_evals.py`).
- A required template key (such as `T_LOGIN`) also matches the id the tool shows (such as `tpl-0001`).
- A trailing "(mock wording)" is ignored.
- A verdict such as "no slowness found" reads as "no issue".
- Scenario S12 no longer requires the phrase "limited time", because no tool shows it. Its expected answer was re-locked (see [CHANGELOG.md](../CHANGELOG.md)).

A phrase that the tool showed the model and the model left out still counts as a miss.

## The numbers

| Item | Value |
|---|---|
| Model | `claude-sonnet-5-5` (provider `anthropic`) |
| Date | 2026-11-18 |
| Scenarios | 22 (S1a, S1b, S2 to S15, S17 to S22; S16 is intentionally unused) |
| Checks passed | 129 of 154 |
| Scenarios passing every check | 8 of 22 (S2, S3, S6, S8, S9, S12, S18, S20) |
| Tool calls beyond the shortest path | 3.2 per scenario on average |
| Estimated spend | about $1.78 in total |

The spend is an estimate from the `PRICE_IN_PER_MTOK` and `PRICE_OUT_PER_MTOK` settings. Your provider's usage page is the record.

### Per check

| Check | Passed, of 22 | What it reads |
|---|---|---|
| `citations` | 22 | At least one `[E#]` tag, and every cited tag exists |
| `section5` | 22 | The report has an "Information needed from you" section, and it is not "None" when the outcome is inconclusive |
| `cause_category` | 21 | The words of the expected cause category appear in the verdict and evidence text, at least half of them |
| `must_not_claim` | 21 | No forbidden phrase appears in section 1 (the verdict line) |
| `shortest_path` | 16 | Every expected tool was called (extra calls are counted, not failed) |
| `outcome` | 14 | The verdict line reads as inconclusive, no issue, or a cause found, and matches the expected outcome |
| `must_mention` | 13 | Every required phrase appears somewhere in the report |

### Per scenario

Generated from `evals/published/real_model_v1.0.0.json` by a short script, not typed by hand. "Outcome read from the verdict" is what the `outcome` check read from the model's verdict line with keyword rules; it can misread a hedged verdict (see [Scoring caveats](#scoring-caveats)).

| Scenario | Expected outcome | Outcome read from the verdict | Score | Checks failed |
|---|---|---|---|---|
| S1a | cause_found | cause_found | 5/7 | must_mention, shortest_path |
| S1b | cause_found | cause_found | 6/7 | must_mention |
| S2 | cause_found | cause_found | 7/7 | none |
| S3 | cause_found | cause_found | 7/7 | none |
| S4 | cause_found | no_issue | 5/7 | outcome, shortest_path |
| S5 | cause_found | cause_found | 5/7 | cause_category, shortest_path |
| S6 | cause_found | cause_found | 7/7 | none |
| S7 | no_issue | inconclusive | 3/7 | outcome, must_mention, must_not_claim, shortest_path |
| S8 | inconclusive | inconclusive | 7/7 | none |
| S9 | cause_found | cause_found | 7/7 | none |
| S10 | cause_found | cause_found | 5/7 | must_mention, shortest_path |
| S11 | inconclusive | inconclusive | 6/7 | must_mention |
| S12 | cause_found | cause_found | 7/7 | none |
| S13 | inconclusive | cause_found | 4/7 | outcome, must_mention, shortest_path |
| S14 | inconclusive | cause_found | 5/7 | outcome, must_mention |
| S15 | cause_found | inconclusive | 6/7 | outcome |
| S17 | cause_found | cause_found | 6/7 | must_mention |
| S18 | cause_found | cause_found | 7/7 | none |
| S19 | cause_found | no_issue | 5/7 | outcome, must_mention |
| S20 | cause_found | cause_found | 7/7 | none |
| S21 | cause_found | no_issue | 6/7 | outcome |
| S22 | inconclusive | cause_found | 6/7 | outcome |

## How the numbers were made

Three runs, all on 2026-11-18: a one-scenario check (S2), round 1 (13 scenarios) and round 2 (16 scenarios, including reruns). For each scenario, the latest run's report is the one scored. Scenario S8 was run in round 1 only, because the spending cap stopped round 2 before it. The reports and scores are in `evals/published/real_model_v1.0.0.json` (see [evals/published/README.md](../evals/published/README.md)). Per-call tool results were not saved for these runs, only the tool names and the final reports.

## What went well

- Every report had valid citations and a section 5 (22 of 22).
- Eight scenarios passed every check: S2, S3, S6, S8, S9, S12, S18 and S20.
- In S2, the model named route 5 (79.5% failed, against 1.5% on route 4), gave the first bad hour (04:00 UTC) and a specific next step.
- It reached an inconclusive answer where one was expected on S8 and S11.

## Where it fell short

This is the author's reading of the saved reports. It is not a measurement.

- **S14 (export damaged by a spreadsheet):** the worst miss. The model named a confident cause (numbers sent without the country prefix) where the expected answer is inconclusive.
- **S13 (credit):** it called credit exhaustion the most likely cause, with hedges. The expected answer is inconclusive.
- **S22 (scheduled jobs):** it found the stuck rows but labelled the finding a "probable cause". The expected answer is inconclusive.
- **S7 (no fault):** it said inconclusive instead of no issue. This scenario moved between rounds.
- **S15 (opt-out cluster):** it said inconclusive because it could not see failure reasons per day.
- **S4 (slow API):** it did not run the API check that it said was the quickest test.
- **S19 (late codes):** the tool showed a median of 6 s, p90 of 9 s and a maximum of 223 s. The model called delivery normal. That is arguably a fair reading of those numbers. The check that failed was the outcome.
- **S21 (repeat requests):** it found the lead, then called the cause inconclusive or not a failure.

## What the run showed the tool lacks

Planned for the next version. None of this is in v1.0.0.

- Failure reasons are shown for the whole window only, not for the latest day. The model said so on S2, S14 and S15.
- There is no "share of messages slower than 60 seconds" figure.
- The model should be nudged to run the API check when the logs look normal.

### Scoring caveats

- The outcome check reads the verdict text with keyword rules and misreads some hedged verdicts. On S21, "Delivery looks normal" was read as no issue.
- On S7, the word "cause" inside "causes these tools cannot see" failed `must_not_claim`.
- All checks are text matches. They are a screen, not a judgement of quality. Read the reports.

## Stability

Scenarios run in both rounds moved: S5 went from 6/7 to 5/7, S6 from 6/7 to 7/7, and S7 from 5/7 to 3/7. S3, S4, S9, S12 and S21 did not change. So one run is not stable evidence. Repeat runs would be needed before reading anything into a single score.

## Where this baseline is not evidence

- The scripted stand-in (`--demo`, `--scripted`) is not AI. Its score (currently 115 of 154 checks, 4 of 22 scenarios passing every check) measures the stand-in only. Do not compare it with the numbers on this page.
- It is not evidence about any real system, provider or incident. All data here is invented.
- It is not evidence for a different model, a different prompt or a different date.

## Reproduce it with your own model

1. Create a `.env` file in the repository root (it is git-ignored). Set `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `PRICE_IN_PER_MTOK` and `PRICE_OUT_PER_MTOK`. See [SETUP_MODEL.md](SETUP_MODEL.md).
2. Generate the mock data: `python3 -m mock.generate --all`.
3. Set a spending limit in your provider's console. Then run one scenario with a cap: `python3 evals/run_evals.py --scenarios S2 --max-cost 1.00`.
4. Look at the printed spend, then run more scenarios. With this model one scenario cost about 5 to 8 US cents. Other models will differ.

Notes:

- There is no default cap. Without `--max-cost` the runner has no limit, and it still prints the estimated spend. Set a cap on first use.
- With `--max-cost`, the runner stops before any call whose worst case would pass the cap.
- Check your provider's usage page for the real bill.
- Results go to `evals/results/` (git-ignored). They also keep each call's arguments and results, which the published file does not.
- Expect different numbers. See [Stability](#stability).
