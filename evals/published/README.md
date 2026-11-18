# Published results

`real_model_v1.0.0.json` is the real-model baseline for v1.0.0. Read it together with [docs/EVALUATION_RESULTS.md](../../docs/EVALUATION_RESULTS.md).

## What the file holds

- The model, provider and date, and a short note on how it was scored.
- The three runs it was drawn from, with estimated spend and the scenarios each one ran.
- Totals: checks passed, scenarios passing every check, per-check counts, extra tool calls and estimated spend.
- For each of the 22 scenarios: the tool names called, time, call and token counts, the expected outcome, the score for each check, and the model's final report.

## What it does not hold

- Per-call tool arguments and results. They were not saved for these runs. Later runs of `evals/run_evals.py` do save them, in `evals/results/` (git-ignored).
- Any real data. Everything comes from the invented mock system.

## How it was produced

Three runs of `evals/run_evals.py` with a real model on 2026-11-18. For each scenario the latest run's report is used. The first-round reports were scored again offline with the revised phrase rule; no new model call was made.

## Do not edit it by hand

It is a record. If you run the evaluation again, write your results elsewhere (the runner does this by default) and describe them as a new run.
