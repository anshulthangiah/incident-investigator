# Quick start

Goal: run the whole loop on your computer in a few minutes, with no key, no account and no internet. At the end you will have read a report and run the tests.

## What you need

- A terminal.
- Python 3.9 or newer. The code uses `from __future__ import annotations`, so 3.9 is the lowest version that works. It was run on 3.9.6 and 3.14. Check yours:

```bash
python3 --version
```

On Windows, use `py -3` where this guide says `python3`.

- `git` (only for the code-changes tool and to clone).

Nothing else. The core uses the Python standard library. A virtual environment is optional here. It becomes useful only when you install the optional database drivers (see [SETUP_DATABASE.md](SETUP_DATABASE.md)).

## 1. Get the code

```bash
git clone https://github.com/anshulthangiah/incident-investigator.git
cd incident-investigator
```

## 2. Optional: create a virtual environment

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell refuses to run the script, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

## 3. Generate the mock data

```bash
python3 -m mock.generate --all
```

This builds one folder per scenario under `mock/generated/` (git-ignored): delivery-log CSV and JSONL files, a SQLite database `mock.db`, a `backend.json`, and two small git repositories. All values are invented and the output is the same every time. To build one scenario only: `python3 -m mock.generate S22`.

## 4. Run the demo

```bash
python3 investigate.py --demo
```

`--demo` uses the scripted stand-in. It is **not AI**: fixed keyword rules choose the tools and a template writes the report. It needs no key. The command starts the mock system for scenario S19 (set by `MOCK_SCENARIO` in `.env.example`), asks the default question, runs the checks and prints a report. To use another scenario:

```bash
python3 investigate.py --demo --mock-scenario S21
```

To ask your own question: `python3 investigate.py --demo "codes arrive late"`.

## 5. Read the report

A report has five sections:

| Section | What it holds |
|---|---|
| 1) Verdict | One line with a confidence level |
| 2) Evidence | Bullets. Each ends with `[E1]`, `[E2]` ... (a tool result) or `[U1]` (something you added) |
| 3) Not checked / limits | What was ruled out, and what could not be checked and why |
| 4) Suggested next steps | What to do |
| 5) Information needed from you | What would confirm or change the verdict, and who can provide it. `None` if nothing |

After the report the tool prints the path of the saved copy, `reports/<session id>.md`. That file also holds every tool result, so you can check each `[E#]` yourself. Open it and look at `E1`.

## 6. Look at what the tools see, without any model

```bash
python3 investigate.py --tools-only --days 3
```

This prints the raw result of five tools for the last 7 days. Other useful commands:

```bash
python3 investigate.py --check                  # which settings and tools are on (values are never shown)
python3 investigate.py --check --live           # also make one call per source
python3 investigate.py --sessions               # list saved investigations
python3 investigate.py --demo --mock-scenario S19 --number 999000000001 "codes arrive late"   # check one number (the AI sees N1)
```

## 7. Continue an investigation

If section 5 asks for more, add a note or a file and continue:

```bash
python3 investigate.py --demo --continue --note "support says about 40 users are affected"
```

Without `--demo` the same flags work with a real model. Then close the case:

```bash
python3 investigate.py --demo --finish --outcome unresolved --yes
```

## 8. Run the tests

```bash
bash tests/run_phase1.sh
```

Expect 211 tests and about 60 seconds. The last line must be `OK`. On Windows, run `python -m unittest discover -s tests -t . -v` instead (the shell script needs bash).

## 9. Run the evaluation runner (optional)

```bash
python3 evals/run_evals.py --scripted
```

It runs all 22 scenarios through the stand-in and prints a score table. This tests the plumbing, not an AI. Most scenarios will not pass every check with the stand-in (it passes 115 of 154 checks), and that is expected. A real-model baseline is published in [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md); the two scores are not comparable. See the README section "Scenarios and evaluation".

### Run the evaluation with your own model

1. Create `.env` (git-ignored) and set `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `PRICE_IN_PER_MTOK` and `PRICE_OUT_PER_MTOK`. See [SETUP_MODEL.md](SETUP_MODEL.md).
2. Set a spending limit in your provider's console.
3. Run one scenario first, with a cap: `python3 evals/run_evals.py --scenarios S2 --max-cost 1.00`.
4. Read the printed spend, then run more: `python3 evals/run_evals.py --scenarios S2 S3 S6 --max-cost 1.00`.

`--max-cost` is optional. There is no default cap: without it the runner has no limit and still prints the estimated spend. To stop early, press Ctrl+C. With a cap, the runner stops before any call that could pass it. The estimate comes from your price settings; your provider's usage page is the record.

## About the live demo link

The README links to `https://anshulthangiah.github.io/incident-investigator/`, a browser replay of four recordings of the scripted stand-in and one of a real model, with a tour and Builder mode. It works only after GitHub Pages is switched on for the repository (Settings, Pages, deploy from the main branch, root folder). To view it locally, run `python3 -m http.server 8765` from the repository root and open `http://localhost:8765`. To record the runs again, run `python3 scripts/record_demo.py`. The page replays; it does not run the command-line tool.

## Clean up

Generated and working files are git-ignored: `mock/generated/`, `sessions/`, `reports/`, `knowledge/`, `inputs/`, `evals/results/`, `.ii_secret`, `data/exports/`. Delete them whenever you like.

## Next

- Use a real language model: [SETUP_MODEL.md](SETUP_MODEL.md)
- Use your own systems: [SETUP_REAL_SYSTEM.md](SETUP_REAL_SYSTEM.md)
