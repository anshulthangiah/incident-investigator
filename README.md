# Incident Investigator

**A product manager types "users say verification codes are late or missing" and gets a short report in which every claim points to the read-only check that supports it, or says "inconclusive" and names what is missing.**

**[Try the live demo](https://anshulthangiah.github.io/incident-investigator/)** (a guided tour of the browser demo; it needs no install)

Version: **v1.0.0**. Release notes: [CHANGELOG.md](CHANGELOG.md). License: MIT.

This is an independent portfolio project. It is not affiliated with any company or product. Every provider, field name, error code, database and incident in this repository is invented.

## What it is, and what it is not

It is:

- A command-line tool, written in Python, that runs a loop. A language model picks one of seven read-only checks, reads the result, and picks the next one, until it can write a report.
- A full mock system: a fake messaging provider (log API and credit call), a fake verification API, a SQLite database, and two small git repositories. 22 invented incidents (scenarios) run against it.
- A way to see the whole loop with no key and no internet, using a scripted stand-in.

It is not:

- **Not AI when you run `--demo`.** The scripted stand-in is a set of fixed keyword rules and a text template. It cannot reason. It exists so anyone can run the full loop offline. Its output starts with the banner `[SCRIPTED STAND-IN, NOT AI]`.
- **Not an accuracy claim.** One real-model baseline is published: one model, one run per scenario, on invented data. It passed 129 of 154 checks and fell short on several scenarios. See [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md).
- **Database adapters fake-tested.** Not tested against a live SQL Server or Postgres. The `mssql` and `postgres` adapters have been exercised only with fake drivers in the tests. SQLite and the mock API run for real.
- **Cannot write to any system except the one approved check.** Tools return summaries only. The one exception, the code-API check, sends one message to your own test number. It is off by default and needs your approval on every run.
- Every provider, field name, error code, database and incident in this repository is invented.

## 60-second quick start

You need Python 3.9 or newer (tested on 3.9.6 and 3.14). The core uses only the standard library. There is nothing to install.

macOS or Linux:

```bash
git clone https://github.com/anshulthangiah/incident-investigator.git
cd incident-investigator
python3 -m mock.generate --all
python3 investigate.py --demo
```

Windows (PowerShell):

```powershell
git clone https://github.com/anshulthangiah/incident-investigator.git
cd incident-investigator
py -3 -m mock.generate --all
py -3 investigate.py --demo
```

`--demo` uses the scripted stand-in and the mock system for scenario S19. Try another scenario with `python3 investigate.py --demo --mock-scenario S21`. Run the tools yourself, with no model at all: `python3 investigate.py --tools-only --days 3`. See what is configured: `python3 investigate.py --check`.

The full walk-through is in [docs/SETUP_QUICKSTART.md](docs/SETUP_QUICKSTART.md).

## What a report looks like

The excerpt below is output from `python3 investigate.py --demo --mock-scenario S21`. It comes from **the scripted stand-in, not from an AI**, so the verdict is a template filled with numbers. A real model writes its own wording and picks its own checks. The layout is the same: five sections, and every claim ends with a tag such as `[E1]` that points to a tool result.

```text
1) Verdict
Rule-based reading: 24.3 percent of requests on the latest day are repeats within the validity window, and a newer code replaces an older one. Confidence: low to medium; check the evidence yourself. [E1]

2) Evidence
- Volume: 4530 requests over 7 days, 88 failed (1.9 percent) [E1]
- Requests per day [E1]
  - 10 Nov: 773 requests, 1.6 percent failed
  - 11 Nov: 740 requests, 2.4 percent failed
  ...
  - 16 Nov: 375 requests, 2.4 percent failed
- Most common failure reason: Recipient unreachable (51 rows). Category: Recipient device. Who fixes it: Usually nothing to fix on the sending side; the phone is off, full or out of coverage. [E1]
- Repeat requests: 127 recipients, 3.4 percent of requests [E1]
- Delivery delay at the provider: median 6.0 s, p90 9.0 s, max 9.0 s [E1]
- Accounts created with an empty language or country prefix on 0 of 7 days [E2]

3) Not checked / limits
- Checks that ran: check_user_data, fetch_delivery_logs. This scripted stand-in does not decide which causes are ruled out, so treat every other cause as not yet checked [E1].
- Not visible to any tool here: the API server's own log, the database scheduler, the code that validates a code, and anything outside the configured sources.
- check_numbers was not run: the PM gave no phone numbers.
- check_code_api was not run: the API check is switched off.

...
```

The full report is also saved to `reports/<session id>.md`, together with every tool result. How the report is built: [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md).

## The seven tools

All tools are read-only. The model chooses a tool and dates. It never supplies a URL, SQL, a path or a credential. Dates are `YYYY-MM-DD` in UTC, at most 14 days per call.

| Tool | Question it answers | Turned on by |
|---|---|---|
| `fetch_delivery_logs` | How many code requests, how many failed and why, which route, sender or template the failures sit on, how fast delivered, how many repeats, per day and per hour? | Exported CSV files in `LOGS_DIR`, or `PROVIDER_API_URL` plus `PROVIDER_API_KEY` |
| `get_credit_balance` | What is the provider account balance now? | `CREDIT_URL` plus `PROVIDER_API_KEY` |
| `check_user_data` | How many accounts were created per day, and how many with an empty language or country prefix? | `DB_ENABLED=true` and a database |
| `check_message_queue` | How many outgoing messages are waiting, for how long, and did they wait too long before sending? | `DB_ENABLED=true` and a database |
| `check_numbers` | What happened to the specific numbers I gave? (the AI sees aliases `N1`, `N2` only) | You pass `--number`, `--numbers-file` or `--prompt-numbers` |
| `check_code_api` | Does the verification API answer, how fast, and does the provider log then show the request? | `PROBE_ENABLED=true`, `CODE_API_URL`, `PROBE_PHONE`, and your approval each run |
| `recent_code_changes` | Which commits landed in the code repositories between two dates? (subjects and file names only) | `REPO_PATHS` |

Inputs, result fields and blind spots of each tool: [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md#the-seven-tools).

## Privacy and safety in six bullets

- The model never sees phone numbers. Numbers you give become aliases (`N1`, `N2`). Saved files hold only keyed fingerprints that cannot be turned back into numbers without your local `.ii_secret` file.
- The model never sees credentials. Keys and tokens are removed from every output, report and session file.
- The database is read with fixed SELECT statements that return counts and timestamps only. The model supplies dates, never SQL.
- Files you add are treated as untrusted data, never as instructions. Phone numbers, emails and IP addresses in them are masked.
- Nothing is written to any remote system. Only one tool does more than read: `check_code_api` sends one real test message to your own number. It is off by default and needs approval on every run.
- You still have jobs to do: use a SELECT-only login, rotate keys, and do not share `data/`, `sessions/`, `reports/` or `knowledge/`. Read [docs/PRIVACY_AND_SAFETY.md](docs/PRIVACY_AND_SAFETY.md).

## Documentation

| Guide | Read it to |
|---|---|
| [docs/SETUP_QUICKSTART.md](docs/SETUP_QUICKSTART.md) | Clone, run the demo, read a report, run the tests |
| [docs/SETUP_MODEL.md](docs/SETUP_MODEL.md) | Connect a language model (Anthropic or OpenAI-compatible) and control cost |
| [docs/SETUP_REAL_SYSTEM.md](docs/SETUP_REAL_SYSTEM.md) | Connect your own delivery provider, with a checklist |
| [docs/SETUP_DATABASE.md](docs/SETUP_DATABASE.md) | Turn on the user-data and queue checks (SQLite, SQL Server, Postgres) |
| [docs/SETUP_CODE_API_CHECK.md](docs/SETUP_CODE_API_CHECK.md) | Turn on the one tool that sends a message |
| [docs/PRIVACY_AND_SAFETY.md](docs/PRIVACY_AND_SAFETY.md) | What the model sees, what it never sees, what is your job |
| [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) | The loop, the report format, memory, limits |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | The messages the tool prints, and the fix for each |
| [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md) | The real-model baseline: numbers, failures, caveats, how to reproduce |
| [docs/KNOWN_ISSUES_AND_ROADMAP.md](docs/KNOWN_ISSUES_AND_ROADMAP.md) | Honest limits and what comes next |
| [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md) | For developers: file layout, every flag, tests, how to add a scenario, tool or provider |
| [spec/SPEC.md](spec/SPEC.md) | The product spec, with an implementation-status section at the end |
| [docs/CURRENT_STATE_AND_GAPS.md](docs/CURRENT_STATE_AND_GAPS.md) | Purpose, what is built and what is not |
| [CHANGELOG.md](CHANGELOG.md) | Release notes |

Every command-line flag is in `python3 investigate.py --help`. The settings are in [`.env.example`](.env.example) and listed in full in [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md#settings).

## Scenarios and evaluation

There are 22 invented incidents in `evals/scenarios/`: S1a, S1b, S2 to S15 and S17 to S22 (the ids are not renumbered). Each file holds the question a PM would type, how the mock data is built, and the expected answer. The expected answer was written before the generator, and a hash lock (`evals/scenarios/expected.lock.json`) makes a test fail if an expected answer changes by accident.

Run them through the same loop and score the reports:

```bash
python3 evals/run_evals.py --scripted                 # the stand-in: tests the plumbing, costs nothing
python3 evals/run_evals.py --scenarios S2 --max-cost 1.00   # your configured model: costs money; --max-cost is optional
```

There is no default spending cap. Without `--max-cost` the runner has no limit, and it prints the estimated spend. Set a cap on first use. Steps to run it with your own model are in [docs/SETUP_MODEL.md](docs/SETUP_MODEL.md).

Seven coarse, text-based checks per scenario: `outcome`, `cause_category`, `must_mention`, `must_not_claim`, `shortest_path`, `citations`, `section5`. The scoring rules are at the top of `evals/run_evals.py`.

Honest status:

- **Real-model baseline (2026-11-18):** `claude-sonnet-5-5` passed 129 of 154 checks over 22 scenarios, and 8 of 22 passed every check. It is one run per scenario on invented data, and scenarios run twice moved by up to two checks, so it is not stable evidence. The scoring rule for required phrases was revised after the first round and the reports were re-scored offline; this is disclosed in [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md), with the failures, the tool gaps it showed and the scoring caveats.
- **Scripted stand-in:** it passes 115 of 154 checks over 22 scenarios. This measures the stand-in only, not any AI. The two scores are not comparable; do not read the scripted numbers as an AI score.
- The stand-in can miss the `must_mention` check because its wording differs from the expected words (for example the expected word `replaced` against the stand-in's `replaces`). This is a limit of the stand-in, not a finding about the tool.
- The checks are text matches. They are a screen, not a judgement of quality. Read the reports.

## Tests

```bash
bash tests/run_phase1.sh
```

211 tests, about 60 seconds, standard library only. They cover the tools, the privacy rules, the database adapters (with fake drivers), the mock stack, the evaluation runner, the command line, and a scan of every file for real-looking IP addresses, phone numbers and key-shaped strings. The vendor-term scan reads an optional private word list (`II_TERMS_FILE`) and is skipped without it. The browser demo has its own tests in `demo/` (see below).

## The browser demo

`demo/` holds a static browser page that replays five recorded runs: four recordings of the scripted stand-in and one of a real model (scenarios S7 no fault, S21 repeat requests replaced earlier codes, S2 provider outage on one route and S8 unanswerable; the page labels which recording is the real model). The text comes from real output of `investigate.py` on the mock system, captured by `scripts/record_demo.py`; the page adds none of its own results. It cannot run the tool or take a new question. It has a guided tour (as many stops as there are ideas to show) and Builder mode, works offline, and makes no network calls. The stand-in is rule-based, not AI; the real-model recording is one run and says nothing about the next.

Run it locally from the repository root:

```bash
python3 -m http.server 8765      # then open http://localhost:8765 (the root page redirects to demo/)
cd demo && node --test           # optional rule tests, needs Node 18 or newer
python3 scripts/record_demo.py   # optional: record the runs again (takes about two minutes)
```

The live link above works only after GitHub Pages is enabled for the repository (Settings, Pages, deploy from the main branch, root folder).

## Project status for v1.0.0

| Part | Status |
|---|---|
| Seven read-only tools, loop, report, memory, privacy features | Built and tested |
| Mock system (logs, credit, verification API, SQLite, git repos) and 22 scenarios | Built and tested |
| Evaluation runner | Built. Scripted run, plus one real-model baseline published (129 of 154 checks; see [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md)) |
| SQLite database checks and mock API | Run for real |
| SQL Server and Postgres adapters | Tested with fake drivers only |
| Anthropic and OpenAI-compatible model adapters | Tested against a local fake server only |
| Web UI, sub-agents, claim verifier | Not built (see the end of [spec/SPEC.md](spec/SPEC.md)) |

## Contributing

Issues and pull requests are welcome. Keep the repository mock-only: use only invented names, the reserved example domains, documentation IP ranges and phone numbers in the 999000 range (the scan tests will fail the build). Run `bash tests/run_phase1.sh` before you send a change. Every change to behaviour, to a scenario's expected answer or to a setting goes into [CHANGELOG.md](CHANGELOG.md) in the same change. To change an expected answer on purpose, follow [docs/BUILD_NOTES.md](docs/BUILD_NOTES.md#add-a-scenario).

## License

MIT, see [LICENSE](LICENSE). The licence covers the code and documents. The mascot images in `demo/assets/` are a personal avatar of the author, are not covered by the MIT licence, and may not be reused.
