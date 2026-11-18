# Known issues and roadmap

An honest list at v1.0.0.

## Known issues and limits

| # | Issue | What it means for you |
|---|---|---|
| 1 | **The `mssql` and `postgres` adapters have been exercised only with fake drivers in tests.** SQLite and the mock API run for real. | Expect first-contact problems on a live SQL Server or Postgres (logins, TLS, object names, type differences). Start with a test database |
| 2 | **The real-model baseline is one run of one model.** It passed 129 of 154 checks on the invented scenarios (8 of 22 scenarios passed every check). Scenarios run twice moved. See [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md). | The project does not claim any accuracy figure for an AI. The model named a confident cause on some scenarios whose expected answer is inconclusive (S13, S14, S22) |
| 3 | **The scripted stand-in is rule-based, not AI.** | Its output shows the plumbing and the layout, not reasoning |
| 4 | **The stand-in can miss the `must_mention` check**, for example on S19 and S21, because its wording differs from the expected words (expected `replaced`, stand-in says `replaces`). | A scripted run scores 115 of 154 checks over 22 scenarios (placeholders). This is a stand-in limit, not a finding about the tool |
| 5 | **The scoring is text matching.** | A correct report in other words can lose a check, and a poor report can pass. Read the reports |
| 6 | **Section 3 brevity and the 700-word aim are enforced only by the prompt.** | A model can ignore them. The code checks tags and the presence of section 5 only |
| 7 | **No claim verifier.** The tool checks that cited tags exist. It does not check that a number in a sentence matches the cited result. | Check important claims against `reports/<id>.md` |
| 8 | **One provider shape.** The live log API and the credit call follow the mock's shape. | Another provider may need a small adapter (`_api_get`, `_norm_api`, `get_credit_balance`). See [SETUP_REAL_SYSTEM.md](SETUP_REAL_SYSTEM.md) |
| 9 | **The CSV reader needs the mock's column names** (`sent_at`, `status`, ...) | Rename the header row of your export |
| 10 | **Timestamps are UTC.** CSV timestamps with no zone are read as UTC, and there is no setting for another zone for files | Add an offset to the column before use |
| 11 | **The database tools read current data.** | Records edited by hand later can hide earlier problems; counts here are current, not historical. The tools say so, and so should you |
| 12 | **Live log API: last 7 days only.** Older dates need exports | |
| 13 | **Some causes are invisible to any tool**: the API server's own log, the database scheduler and its job history, the code that validates a code. | The report names who to ask (engineering, DevOps, the DBA). Scenario S22 shows this |
| 14 | **Prompt injection is reduced, not removed.** | See [PRIVACY_AND_SAFETY.md](PRIVACY_AND_SAFETY.md) |
| 15 | **Only English questions** are supported in the prompt and stand-in rules | |
| 16 | **Small local models** often call tools badly | Expect weaker results |
| 17 | **Windows:** the test script is a bash file | Use `python -m unittest discover -s tests -t . -v` |
| 18 | The mock clock is pinned to 2026-11-16 12:00 UTC (`MOCK_NOW`) so the data is repeatable | Dates in mock reports are in November 2026 |

## What is not built from the spec

The first spec described a web chat app, sub-agents and a claim verifier. v1.0.0 is a command-line tool. See "Implementation status at v1.0.0" at the end of [spec/SPEC.md](../spec/SPEC.md) for the rule-by-rule list.

## Ideas for later (not promised)

- A web interface (the spec's chat window, a trace view, a stop button).
- More provider adapters, with a settings-driven column map for CSV files and a configurable log API shape.
- A claim verifier that checks the numbers in each sentence against the cited result.
- More scenarios, including ones with several faults at once and ones where the right answer is "no issue".
- A live Postgres and SQL Server test run, and published results.
- Repeat runs of the real-model evaluation, with failed runs kept. The baseline is one run per scenario.
- Next version, from the baseline: show failure reasons for the latest day, not only the whole window (the model said it could not see them on S2, S14, S15).
- Next version: a "share of messages slower than 60 seconds" figure.
- Next version: nudge the model to run the API check when the logs look normal (S4).
- Next version: fix scoring misreads. The outcome check misreads some hedged verdicts (S21), and "cause" inside "causes these tools cannot see" failed `must_not_claim` on S7.
- Sub-agents for parallel repository checks.
- A setting for the zone of CSV files.

## Reporting a problem

Open an issue. Do not include numbers, keys or hostnames. A copy of the failing command and the message printed is enough.
