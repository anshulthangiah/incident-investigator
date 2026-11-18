# Build notes (for developers)

How the code is laid out, every flag, every tool, how the tests work, and how to extend it. Everything here was checked against the code at v1.0.0.

Requirements: Python 3.9 or newer, standard library only. Optional: `pymssql` (SQL Server) and `psycopg[binary]` (Postgres).

## File layout

| Path | What it is |
|---|---|
| `investigate.py` | The command line. `build_parser()` defines every flag. `main()` starts the mock stack if asked, then `_main()` routes to knowledge, finish, sessions, check, tools-only, or the investigation |
| `investigator/config.py` | Settings (`get`, `get_int`, `get_float`, `get_bool`), the `.env` loader, `redact()`, the TLS context, the per-install key and `fingerprint()`, `now_utc()` |
| `investigator/tools.py` | The seven tools, the registry `TOOLS`, `availability()` (preflight), `schemas()`, log sources (CSV and live API) |
| `investigator/db.py` | Database adapters (`sqlite`, `mssql`, `postgres`), fixed SQL builders, `assert_select`, friendly error text |
| `investigator/agent.py` | The loop (`run`), the system prompt `SYSTEM`, sessions (`new_state`, `save_state`, `load_state`), `make_gist` |
| `investigator/llm.py` | Model providers: `call_anthropic`, `call_openai_compatible`, `get_llm` |
| `investigator/numbers.py` | Aliases `N1`.., `scrub()`, number parsing |
| `investigator/inputs.py` | Files and notes added with `--file` and `--note`, masking |
| `investigator/reasons.py` | Failure-reason glossary lookup from `data/reason_glossary.json` |
| `investigator/knowledge.py` | Memory: built-in patterns `SEEDS`, saved cases, `validate_gist`, `add_case` |
| `investigator/demo.py` | The scripted stand-in `ScriptedModel` (keyword rules and a template; not AI) |
| `mock/generate.py` | Builds one scenario folder in `mock/generated/<id>/` from `evals/scenarios/<id>.json`. Deterministic (seeded from the id) |
| `mock/api_server.py` | Mock verification API and mock provider log and credit API |
| `mock/db_builder.py` | Builds `mock.db` (tables `accounts`, `sessions`, `outbox`) |
| `mock/repos.py` | Builds the two small git repositories `code_service` and `message_gateway` |
| `mock/stack.py` | `start(sid)`: generates if needed, starts the mock API on a free local port, sets the environment for this process only |
| `evals/scenarios/S*.json` | One file per scenario: `question`, `generate`, `expected` |
| `evals/scenarios/expected.lock.json` | Hash of every `expected` block |
| `evals/lock_expected.py` | Rewrites the lock file |
| `evals/run_evals.py` | Runs scenarios through the agent loop and scores them |
| `data/reason_glossary.json` | Failure-reason wording for the mock provider |
| `data/exports/` | Delivery-log CSV files (git-ignored) |
| `tests/` | `test_investigator.py`, `test_phase1_mock_stack.py`, `run_phase1.sh` |
| `spec/SPEC.md` | The product spec |
| `docs/` | These guides |
| `scripts/record_demo.py` | Runs `investigate.py --demo` on four scenarios (S7, S21, S2, S8), adds one recording read from `evals/published/real_model_v1.0.0.json` (the real model's S2 report), and writes `demo/recordings.js` (deterministic). Also records the scenario and test counts for the demo footer |
| `demo/`, `index.html` | The static browser replay of those recordings, with a tour and Builder mode, and its tests (Node) |
| `.env.example` | Every setting, with defaults. Used if there is no `.env` |

Created at run time (all git-ignored): `mock/generated/`, `sessions/`, `reports/`, `knowledge/`, `inputs/`, `evals/results/`, `.ii_secret`.

## Command-line flags

All flags are in `python3 investigate.py --help`.

| Flag | Meaning | Example |
|---|---|---|
| `symptom` (positional) | The question, in plain English | `python3 investigate.py "codes arrive late"` |
| `--demo` | Use the scripted stand-in (not AI, no key) | `python3 investigate.py --demo` |
| `--mock-scenario ID` | Start the local mock stack for a generated scenario | `python3 investigate.py --demo --mock-scenario S21` |
| `--continue` | Continue the latest investigation | `python3 investigate.py --continue --note "40 users"` |
| `--session ID` | Pick the session for `--continue` or `--finish` | `python3 investigate.py --continue --session 20261117_101500` |
| `--file PATH` | Add a file (repeatable) | `--file export.csv` |
| `--note TEXT` | Add a typed note (repeatable) | `--note "support saw this at 9 am"` |
| `--ask` | After a report that asks for more, prompt for files and notes | `python3 investigate.py "..." --ask` |
| `--number N` | A phone number to check (repeatable). The model sees an alias | `--number 999000000001` |
| `--numbers-file PATH` | A text file of numbers (commas, spaces or lines) | `--numbers-file list.txt` |
| `--prompt-numbers` | Type numbers at a hidden prompt | `--prompt-numbers` |
| `--approve-probe` | Allow the code-API check for this run | `--approve-probe` |
| `--finish` | Close the investigation and save a case note | `python3 investigate.py --finish` |
| `--outcome X` | With `--finish`: `confirmed`, `probable`, `unresolved`, `discard` | `--outcome confirmed` |
| `--cause TEXT` | With `--finish`: the cause in your words | `--cause "stuck worker"` |
| `--yes` | With `--finish`: save without asking | `--yes` |
| `--knowledge` | List what the tool remembers | `python3 investigate.py --knowledge` |
| `--sessions` | List saved investigations | `python3 investigate.py --sessions` |
| `--check` | Show configuration and which tools are on | `python3 investigate.py --check` |
| `--live` | With `--check`: one call per source | `--check --live` |
| `--tools-only` | Run the tools without any model | `python3 investigate.py --tools-only --days 3` |
| `--date YYYY-MM-DD` | End date for `--tools-only` and `--live` (UTC; default today, or the mock date) | `--tools-only --date 2026-11-15` |
| `--days N` | Number of days ending at `--date` (default 1) | `--days 3` |

Notes: `--tools-only` runs `fetch_delivery_logs`, `get_credit_balance`, `recent_code_changes`, `check_user_data` and `check_message_queue`. It does not run `check_numbers` or `check_code_api`. `--check --live` runs the same five for one day.

Exit codes: 0 normal, 1 missing symptom or bad `--finish` input, 2 a tool or model error.

## The seven tools

All dates are `YYYY-MM-DD` in UTC, `start_date` and `end_date` (or `since_date` and `until_date` for `recent_code_changes`), at most 14 days. The model supplies nothing else. Defined in `investigator/tools.py`, registered in `TOOLS`.

| Tool | Settings that enable it | Result fields | Cannot see |
|---|---|---|---|
| `fetch_delivery_logs` | CSV in `LOGS_DIR`, or `PROVIDER_API_URL` + `PROVIDER_API_KEY`; `LOGS_SOURCE` | `source`, `days`, `total`, `delivered`, `failed`, `failure_rate_pct`, `requests_per_day`, `failure_rate_pct_per_day`, `days_without_data`, `failure_reasons`, `failures_by_category`, `templates`, `distinct_recipients`, `recipient_digit_lengths`, `repeat_requests`, `delivery_delay_s` (median, p90, max), `requests_per_hour_utc` (3 days or fewer), `failures_by_group` (per route, sender and template: `whole_window` and `latest_day` lists of `{value, requests, failed, failure_rate_pct}`, groups with at least 20 requests, at most 6, worst rate first; a dimension the source lacks is skipped and named in `notes`), `latest_day_utc`, `failures_by_hour_latest_day` (`{hour, requests, failed, failure_rate_pct}` per UTC hour), `concentration` (`null`, or `{dimension, value, failure_rate_pct, other_rate_pct, share_of_failures_pct, first_bad_hour_utc}` when on the latest day one route, sender or template fails at 3 times the rate of all other rows, with at least 20 failed rows and at least 60 percent of that day's failures; `first_bad_hour_utc` is the first hour whose two-hour window has at least 30 percent failures over at least 5 requests), `api_failed_calls`, `data_quality`, `notes` | Requests that never reached the provider (only missing volume shows). Message text and recipient numbers (breakdowns hold counts and rates only). Anything outside the export folder or API |
| `get_credit_balance` | `CREDIT_URL`, `PROVIDER_API_KEY`, `CREDIT_KEY_HEADER`, `CREDIT_PER_REQUEST` | `balance`, `requests_remaining_at_current_rate`, `note` | The balance at an earlier time. Credit is shared by every message type |
| `check_user_data` | `DB_ENABLED=true` and `DB_*` | `database`, `timestamps_stored_as`, `days` (`created_date_utc`, `new_users`, `locale_empty`, `dial_code_empty`), `limits`, `replica` | Past states: it reads current data. Account rows |
| `check_message_queue` | `DB_ENABLED=true`, `DB_*`, `DB_QUEUE_*`, `QUEUE_BATCH_SIZE`, `QUEUE_TICK_S`, `CODE_EXPIRY_MIN` | `as_of_utc`, `waiting_now`, `estimated_minutes_to_clear_waiting`, `estimate_basis`, `rows_by_created_day`, `unusual_statuses_in_window`, `wait_before_sent`, `newest_row_recent`, `queue_note`, `newest_row_created_utc`, `replica`, `reading`, `limits` | Body and destination (never read), so code rows cannot be told from other texts. Whether the worker or a scheduled job runs |
| `check_numbers` | Numbers from `--number`, `--numbers-file`, `--prompt-numbers`; logs; database optional | `numbers` (`alias`, `requests`, `delivered`, `failed`, `requests_within_2_min_of_previous`, `latest_requests`), `summary`, `days_without_data`, `user_records` (flags, timestamps, that account's own session records), `notes` | The number itself (alias only). User records need the numbers re-supplied in the same run |
| `check_code_api` | `PROBE_ENABLED=true`, `CODE_API_URL`, `PROBE_PHONE`, approval | `called_at_utc`, `sent_to`, `elapsed_ms`, `http_status`, `response_message`, `result`, `reading`, `SECURITY_FINDING`, `provider_log` | The API server's own log. Whether the incident happened earlier. Takes no parameters |
| `recent_code_changes` | `REPO_PATHS` | `repos` (per repository: `commits` with `commit`, `date`, `author`, `subject`, `files`; or `error`), `note` | Code. Only subjects and file names, 30 commits per repository |

## Settings

Every setting in `.env.example`, plus the extra ones. Empty means "not set"; the default applies. Booleans accept `1`, `true`, `yes`, `on`. Real environment variables win over `.env`, which wins over `.env.example` (only one of `.env` and `.env.example` is read).

| Group | Name | Default | Meaning |
|---|---|---|---|
| Mock | `MOCK_SCENARIO` | `S19` (in `.env.example`) | Start the mock stack for this scenario. Comment out to use your own systems |
| Mock | `MOCK_NOW` | unset | Pins the clock for the mock stack. Set automatically. Leave unset otherwise |
| Model | `LLM_PROVIDER` | `anthropic` | `anthropic` or `openai_compatible` |
| Model | `LLM_API_KEY` | empty | API key. Never printed |
| Model | `LLM_MODEL` | empty | Model name |
| Model | `LLM_BASE_URL` | empty | Empty = provider default |
| Model | `LLM_TIMEOUT_S` | `120` | Seconds per model call |
| Model | `LLM_TOKENS_PARAM` | `max_tokens` | Name of the output-limit field (some services want `max_completion_tokens`) |
| Limits | `MAX_STEPS` | `12` | Tool steps per round |
| Limits | `MAX_SECONDS` | `120` | Seconds per round |
| Limits | `MAX_OUTPUT_TOKENS` | `8000` | Output limit |
| Cost | `PRICE_IN_PER_MTOK` | `2` | Input price per million tokens |
| Cost | `PRICE_OUT_PER_MTOK` | `10` | Output price per million tokens |
| Logs | `LOGS_SOURCE` | `auto` | `auto`, `csv`, `api` |
| Logs | `LOGS_DIR` | `data/exports` | Folder of export CSVs |
| Logs | `PROVIDER_API_URL` | empty | Live log API base URL |
| Logs | `PROVIDER_API_KEY` | empty | Key for the log API and the credit call |
| Logs | `REASON_GLOSSARY` | `data/reason_glossary.json` | Failure-reason file |
| Credit | `CREDIT_URL` | empty | Balance call URL |
| Credit | `CREDIT_KEY_HEADER` | `X-Api-Key` | Name of the request header that carries the key |
| Credit | `CREDIT_PER_REQUEST` | `0.05` | Credit used per request |
| Repos | `REPO_PATHS` | empty | Comma-separated git repository paths |
| Database | `DB_ENABLED` | `false` | Master switch |
| Database | `DB_KIND` | `sqlite` | `sqlite`, `mssql`, `postgres` |
| Database | `DB_HOST` | empty | Host or `host:port` or `host,port` |
| Database | `DB_PORT` | empty | Port (default 1433 or 5432) |
| Database | `DB_NAME` | empty | Database name; for SQLite the file path |
| Database | `DB_USER` | empty | Login |
| Database | `DB_PASSWORD` | empty | Password. Never printed |
| Database | `DB_SSLMODE` | `prefer` | Postgres only |
| Database | `DB_TDS_VERSION` | empty | SQL Server only (for example `7.3`) |
| Database | `DB_REPLICA` | `false` | Connection is a read replica |
| Database | `DB_TIMESTAMP_TZ` | `UTC` | Only `UTC` is accepted; for accounts, sessions and outbox |
| Database | `DB_USERS_OBJECT` | empty | Empty = `accounts` (`public.accounts` on Postgres) |
| Database | `DB_DEVICES_OBJECT` | empty | Empty = `sessions`; `none` switches off |
| Database | `DB_QUEUE_OBJECT` | empty | Empty = `outbox` |
| Database | `DB_COL_USER_ID` | `id` | Accounts column |
| Database | `DB_COL_USERNAME` | `login_ref` | |
| Database | `DB_COL_LOCALE` | `language` | |
| Database | `DB_COL_DIAL_CODE` | `country_prefix` | |
| Database | `DB_COL_ACTIVE` | `is_active` | |
| Database | `DB_COL_PHONE_CONFIRMED` | `phone_verified` | |
| Database | `DB_COL_CREATED` | `created_at` | |
| Database | `DB_COL_UPDATED` | `updated_at` | |
| Database | `DB_COL_DEV_USERID` | `account_id` | Sessions column |
| Database | `DB_COL_DEV_CODE_EXPIRY` | `code_valid_until` | |
| Database | `DB_COL_DEV_LOGIN` | `last_seen_at` | |
| Database | `DB_QCOL_CHANNEL` | `kind` | Outbox column |
| Database | `DB_QCOL_STATUS` | `state` | |
| Database | `DB_QCOL_CREATED` | `created_at` | |
| Database | `DB_QCOL_UPDATED` | `updated_at` | |
| Queue | `QUEUE_BATCH_SIZE` | `20` | Rows per channel per tick |
| Queue | `QUEUE_TICK_S` | `30` | Seconds per tick |
| Queue | `CODE_EXPIRY_MIN` | `10` | Minutes a code stays valid; also the repeat-request window |
| Code API | `PROBE_ENABLED` | `false` | Master switch |
| Code API | `CODE_API_URL` | empty | Endpoint |
| Code API | `CODE_API_TOKEN` | empty | Optional bearer token. Never printed |
| Code API | `CODE_API_BODY_TEMPLATE` | empty | Optional JSON body with `{country_prefix}`, `{phone}`, `{client}` |
| Code API | `PROBE_PHONE` | `999000000001` | Your own test number |
| Code API | `PROBE_COUNTRY_PREFIX` | `+99` | |
| Code API | `PROBE_CLIENT` | `incident-probe` | |
| Code API | `PROBE_MAX_PER_RUN` | `2` | |
| Code API | `PROBE_MIN_GAP_S` | `15` | |
| Code API | `PROBE_TIMEOUT_S` | `30` | |
| Code API | `PROBE_SLOW_MS` | `5000` | |
| Code API | `PROBE_LOG_WAIT_S` | `60` | |
| Code API | `PROBE_LOG_POLL_S` | `5` | |
| Code API | `PROBE_EXPECT_TEXT` | `Request accepted` | |
| Numbers | `PHONE_LEADING_DIGITS` | empty | Optional rule: allowed first digits of a national number (empty means any digit) |
| Files | `STATE_DIR` | project folder | Where `sessions/`, `reports/`, `knowledge/`, `inputs/` and `.ii_secret` go |
| Files | `SECRET_FILE` | `STATE_DIR/.ii_secret` | Path of the key file |
| Mock only | `MOCK_NOTIFY_API_TOKEN`, `MOCK_PROVIDER_KEY`, `MOCK_PORT` | `mock-token-not-secret`, `mock-provider-key-not-secret`, `8099` | Used only when you run `python3 -m mock.api_server <scenario folder>` by hand |

## Tests

```bash
bash tests/run_phase1.sh
```

211 tests, about 60 seconds. The script runs `python3 -m unittest discover -s tests -t . -v`.

| File | Tests | Covers |
|---|---|---|
| `tests/test_investigator.py` | 139 | Config and redaction, numbers and privacy, glossary, delivery logs, database adapters (with `FakeCursor` and `FakeConn`), queue, code-API check, memory, the loop, preflight, the stand-in, model providers (against `FakeLlmServer`), scenarios S20 to S22, mock endpoints, the eval runner, the command line, and a repository-wide scan (`TestRepoWideScan`) |
| `tests/test_phase1_mock_stack.py` | 52 | Scenario files and the lock, determinism and privacy of generated data, export layout, that every fault is present, repositories, user-data scenarios, mock API |

`TestRepoWideScan` fails if any file contains a real-looking IP address (only `203.0.113.x`, `10.0.0.x` and localhost are allowed), a 12-digit number outside `999000xxxxxx`, or a key-shaped string. A separate vendor-term check reads an optional private word list: set `II_TERMS_FILE` to a plain-text file with one lowercase word per line (the repository holds no word list). Without it that check is skipped with the message "set II_TERMS_FILE to a private word list to enable the term scan". The scanner itself is `tests/term_scan.py`; its planted-word test uses only an invented neutral word. The suite also checks that `.gitignore` covers `.env`, `.ii_secret`, `sessions/`, `reports/`, `knowledge/`, `inputs/`, `evals/results/`, and that no `.git` folder exists in the project. This applies to the docs too.

Browser demo tests: `cd demo && node --test` (needs Node 18 or newer).

## Add a scenario

Order matters. The expected answer comes first so the generator cannot be bent to fit it.

1. Write `evals/scenarios/S23.json` with `id`, `title`, `question`, `generate` and `expected`. Copy a close sibling. Start with `expected`:
   - `outcome`: `cause_found`, `inconclusive` or `no_issue`
   - `cause_category`: words joined by `_` (scored by word overlap; `none` for no cause)
   - `layer`, `culprit_repo`
   - `must_mention`: phrases that must appear in the report
   - `must_not_claim`: phrases that must not appear in the verdict line
   - `shortest_path`: the tools a good investigation calls
   - `notes`: why, in plain words
2. Make the generator produce it. `generate.faults` is a list of `{"type": ...}` entries. The fault types the generator handles are in `apply_faults` in `mock/generate.py` (for example `format_strip`, `missing_locale`, `upstream_hang_drop`, `credit_exhausted`, `optout_cluster`, `template_reject`, `route_failure`, `late_delivery`, `repeat_requests`, `queue_backlog`, `api_save_error`, `scheduled_job_stopped`). A new fault type needs a branch there, and a test that it is handled.
3. Build and look at it: `python3 -m mock.generate S23`, then `python3 investigate.py --demo --mock-scenario S23`.
4. Lock the expected answer: `python3 evals/lock_expected.py`.
5. Run `bash tests/run_phase1.sh`.
6. Record it in `CHANGELOG.md`. **Changing the `expected` block of an existing scenario after results exist must be written in the CHANGELOG** and in `evals/scenarios/README.md`. Adding a scenario leaves the existing hashes unchanged.

Use only invented values: `999000xxxxxx` numbers, `203.0.113.x` addresses, wording marked `(mock wording)`.

## Add a tool

1. Write the function in `investigator/tools.py`. It takes only string dates (or nothing), returns a small dict (counts, rates, timings), and raises `ToolError` with a message that holds no URL or credential. It must never return a number, name, message text or user row.
2. Register it in `TOOLS`: `name: (function, description, {param: "YYYY-MM-DD"})`. The description is what the model reads. Say when to use it and what it cannot see.
3. Add it to `availability()` with a one-line reason when it cannot run. Tools whose reason is not `None` are hidden from the model and listed in the prompt as not available.
4. If it changes anything outside the tool (for example sends a message), add it to `NEEDS_CONFIRM` so it needs approval on every run. Prefer not to build such a tool.
5. Read-only database tools: add the SQL as a builder in `investigator/db.py`, with dates as parameters. `execute()` refuses anything that is not a single SELECT.
6. Mention it in the `SYSTEM` prompt in `investigator/agent.py` if the model needs rules for it.
7. If `--tools-only` should run it, add it in `_main()` of `investigate.py`.
8. Write tests. Update `docs/` and `CHANGELOG.md`. `knowledge.validate_gist` accepts only real tool names in `first_checks`, so memory picks it up automatically.

## Add a provider

Model provider (see `investigator/llm.py`): add a function `call_<name>(messages, system, use_tools=True)` that takes the internal Anthropic-style messages and returns `{"content": [...], "stop_reason": ..., "usage": {"input_tokens", "output_tokens"}}`. Register it in `provider_name()` and `get_llm()`. Most services already work with `LLM_PROVIDER=openai_compatible` and a base URL.

Delivery-log provider (see [SETUP_REAL_SYSTEM.md](SETUP_REAL_SYSTEM.md)): for CSV, no code change is needed if the columns match. For a live API, change `_api_get` (path, headers, paging) and `_norm_api` (field mapping) in `investigator/tools.py`. To make the mock follow your shape, change `mock/api_server.py` the same way, and keep the tests passing. The glossary is data, not code: replace `data/reason_glossary.json`.

Database: add an `Adapter` to `ADAPTERS` in `investigator/db.py` (connection function, error rewriter, SQL snippets, default object names).

## Evaluation runner

```bash
python3 evals/run_evals.py --list
python3 evals/run_evals.py --scripted
python3 evals/run_evals.py --scripted --scenarios S19 S21
python3 evals/run_evals.py --scenarios S2 --max-cost 1.00   # your configured model: needs LLM_* settings, costs money
python3 evals/run_evals.py --scripted --out /tmp/results
```

Flags: `--scripted`, `--scenarios IDS...`, `--out DIR`, `--list`, `--max-cost USD`. `--max-cost` is optional; there is no default cap. The runner stops before any call whose worst case would pass the cap, and always prints the estimated spend. Results go to `evals/results/<run id>.json` (git-ignored); real-model results also keep each call's arguments and results (`evidence`). The published baseline is in `evals/published/` ([results page](EVALUATION_RESULTS.md)). A scripted run is marked `scripted_stand_in: true`. The checks and their rules are in the module docstring of `evals/run_evals.py`. The runner approves the code-API check for the run (mock stack only).

## Conventions

- Standard library only in the core. Keep optional drivers optional and imported only when used.
- Use only invented names, the reserved example domains, documentation IP ranges and phone numbers in the 999000 range. Run the test suite before every change.
- Plain words in messages. A message that reaches the user must contain no URL, host, user name or password.
- Every change goes into `CHANGELOG.md`.
- Never run `git init` inside a folder that holds generated data; the mock stack creates its own small repositories under `mock/generated/`.
