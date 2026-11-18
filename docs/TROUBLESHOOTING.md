# Troubleshooting

The messages below are the ones the tool prints. Each has a cause and a fix. First, always run:

```bash
python3 investigate.py --check
```

It shows what is set and which tools are on. Values are never shown.

## Settings and model

| Message | Cause | Fix |
|---|---|---|
| `(mock stack for scenario S19 running on ...)` appears when you wanted your own system | `MOCK_SCENARIO` is set (it is active in `.env.example`) | Put `#` in front of `MOCK_SCENARIO` in `.env`. Check that no `MOCK_SCENARIO` is set in your shell |
| `LLM_API_KEY and LLM_MODEL must be set in .env (or run with --demo for the scripted stand-in)` | No key or model name | See [SETUP_MODEL.md](SETUP_MODEL.md) |
| `LLM_API_KEY holds a login (OAuth) token from a chat app, which the API does not accept...` | The key starts with `sk-ant-oat` | Create an API key in the provider's console and use that |
| `LLM_API_KEY must be set in .env (only a local server on localhost may run without one)` | `openai_compatible` with a remote URL and no key | Set the key, or use a localhost URL |
| `LLM_PROVIDER must be anthropic or openai_compatible` | Typo | Use one of the two values |
| `LLM_BASE_URL must start with https:// (plain http is allowed only for localhost)` | An `http://` URL to a remote host | Use `https://` |
| `model call failed (HTTP 401: ...)` or `(HTTP 403 ...)` | Key refused | Check the key and the account |
| `model call failed (HTTP 400: ...)` | Wrong model name, or the service wants `max_completion_tokens` | Check `LLM_MODEL`. Try `LLM_TOKENS_PARAM=max_completion_tokens` |
| `model call failed (HTTP 429 ...)` | Rate limit or no balance | Wait, or check your plan |
| `model call failed (TimeoutError)` or `(URLError)` | Slow or unreachable service | Raise `LLM_TIMEOUT_S`. Check the network and URL |
| `the model service answered in an unexpected format` | The service is not OpenAI-compatible, or does not support tools | Check `LLM_BASE_URL` and that the model supports tool calling |
| The report is cut off, `The report was cut off ...` | Reached `MAX_OUTPUT_TOKENS` | Run `python3 investigate.py --continue` or raise the setting |
| `Stopped: step limit of 12 reached before a conclusion.` | `MAX_STEPS` too small for this case | Raise `MAX_STEPS`, then `--continue` |
| `Stopped: time limit of 120s reached before a conclusion.` | A slow model or slow source | Raise `MAX_SECONDS` |
| `The report cites no evidence tags.` / `cites evidence that does not exist` / `has no 'Information needed from you' section.` | The model ignored the format | Run `--continue`. A weaker model does this more often. Do not trust such a report |

## Delivery logs and credit

| Message | Cause | Fix |
|---|---|---|
| `No log rows for: 2026-11-10. The export folder holds data for: ...` | No export file covers that date | Add an export: `python3 investigate.py --continue --file path/to.csv`. This is not evidence of zero traffic |
| `Recent dates need PROVIDER_API_URL and PROVIDER_API_KEY to be read from the live API.` | Last 7 days, no live API, and no export for them | Set both, or export the recent dates |
| `PROVIDER_API_URL and PROVIDER_API_KEY must both be set` | `LOGS_SOURCE=api` without them | Set both, or use `auto` or `csv` |
| `the live log API serves only the last 7 days; use exported files for older dates` | `LOGS_SOURCE=api` with an older date | Use `LOGS_SOURCE=auto` |
| `the provider log call failed (HTTP 401)` | Key rejected | Check `PROVIDER_API_KEY` |
| `the provider log call failed (HTTP 404)` | The path differs on your provider | See "Live log API" in [SETUP_REAL_SYSTEM.md](SETUP_REAL_SYSTEM.md): adapt `_api_get` |
| `the provider log call failed (URLError: ...)` | Cannot connect | Check the URL, VPN, network |
| `PROVIDER_API_URL must start with https:// ...` | Plain http to a remote host | Use https |
| `YYYY-MM-DD: the API reported N rows but returned M; figures for this day are INCOMPLETE` | The API paged or truncated | Use an export for that day, or adapt `_api_get` to page |
| `...; those days were read from the export folder instead` | The live call failed and the tool fell back | Fix the API, or accept the export |
| `data_quality: N of M recipient values look re-saved by a spreadsheet` | Someone opened and saved the CSV in a spreadsheet | Export again straight to CSV |
| `LOGS_SOURCE must be auto, csv or api` | Typo | Fix it |
| `dates must be YYYY-MM-DD (UTC)`, `end date is before start date`, `at most 14 days per call` | Bad dates | Fix `--date` / `--days` (tools-only) |
| `skipped: file not found`, `file type .xlsx is not supported ...` | Wrong path or file type | Use `.csv .txt .md .log .json .tsv`. For other files, type what they show with `--note` |
| `... is larger than 25 MB; export a shorter period` | Export too big | Export fewer days |
| `... has a header but no rows` | Empty export | Re-export |
| `CREDIT_URL and PROVIDER_API_KEY must both be set` | Credit tool not configured | Set both, or ignore it |
| `CREDIT_KEY_HEADER must be only a header name ...` | Something other than a plain header name was put in it | Put only the name, for example `X-Api-Key` |
| `the credit response was not a number or an object with a 'balance' number` | The credit call returned text or JSON in another shape | Make the provider reply `{"balance": <number>, "units": "credits"}` or a bare number, or adapt `get_credit_balance()` |

## Database

| Message | Cause | Fix |
|---|---|---|
| `the database checks are switched off (DB_ENABLED is not true; ...)` | Master switch off | `DB_ENABLED=true` |
| `not set: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD` | Missing settings for SQL Server or Postgres | Set them |
| `login was rejected (check DB_USER and DB_PASSWORD)` | Wrong user or password | Fix them. Ask the DBA |
| `the login cannot open that database (check DB_NAME and the login's permissions)` | SQL Server: no access to that database | Ask the DBA |
| `the login has no SELECT permission on that object` | The login cannot read the view | Ask the DBA to grant SELECT on the view |
| `table or column not found (check the DB_*_OBJECT and DB_COL_* settings)` | Wrong object or column name | Fix the names. Postgres folds unquoted names to lower case |
| `could not reach the server (is the VPN connected? is DB_HOST correct?)` | Network | Connect the VPN. Check `DB_HOST` and port |
| `the database server did not answer within 3 seconds (is the VPN connected? is DB_HOST correct?)` | Preflight socket test failed | Same |
| `the server refused this connection (login, SSL mode or allowed address); see DB_SSLMODE` | Postgres refused (no `pg_hba` entry, SSL) | Try `DB_SSLMODE=require`. Ask the DBA to allow your address |
| `database not found (check DB_NAME)` | Postgres | Fix the name |
| `pymssql is not installed ...` / `psycopg is not installed ...` | Optional driver missing | See [SETUP_DATABASE.md](SETUP_DATABASE.md) |
| `DB_KIND must be one of: sqlite, mssql, postgres` | Typo | Fix |
| `DB_HOST should be a host name or address, optionally with a port ...` | Bad host text | Use `203.0.113.5,1433` or `db.example.com:5432` |
| `DB_USERS_OBJECT must be a plain table or view name ...` | Object name not valid | Remove anything but the plain name, for example `reporting.v_accounts` |
| `... must be a plain column name (letters, digits, underscore)` | A `DB_COL_*` or `DB_QCOL_*` value is not plain | Fix it |
| `set DB_TIMESTAMP_TZ to UTC (the only zone the tools read; convert in the view if needed)` | Other value | Use `UTC`, or convert to UTC in the view |
| `the SQLite file in DB_NAME does not exist (run: python3 -m mock.generate --all)` | Mock data not generated | Run that command |
| `the database file is locked; try again` | SQLite busy | Try again |
| `queue_note: The newest row in this queue table was created ... BEFORE the window asked about` | The table has nothing recent for the window. A replica far behind can cause this | Check `DB_NAME` and `DB_QUEUE_OBJECT` and ask where current queue data is held. Do not read an empty or old queue as healthy |
| `queue_note: The queue table has no rows at all` | The table is empty or was cleared | Same |
| `replica: ... may trail the live database` | `DB_REPLICA=true` | Informational. Read counts as "at least as of some minutes ago" |
| TLS or handshake error on SQL Server | Old server protocol | Set `DB_TDS_VERSION` (for example `7.3`) after asking the DBA. See [SETUP_DATABASE.md](SETUP_DATABASE.md) |
| `no data for a day` in user or queue counts | The table has no row in that window | The check reads current data. A zero for a past day does not prove the fault did not happen |

## Numbers

| Message | Cause | Fix |
|---|---|---|
| `skipped one entry: that does not look like a phone number (10 to 13 digits)` | Wrong length, or `PHONE_LEADING_DIGITS` is set and the first national digit is not in it | Check the number. If you set `PHONE_LEADING_DIGITS`, make sure it lists every digit your numbers start with, or leave it empty |
| `at most 20 numbers per investigation` | Too many | Split into two investigations |
| `no phone numbers were given for this investigation ...` | `check_numbers` without numbers | Use `--number`, `--numbers-file` or `--prompt-numbers` |
| `user_records: not checked: numbers are kept only in memory for the run that received them` | You continued without the numbers | Pass `--number` again |
| `skipped: cannot read <file>` | `--numbers-file` path wrong | Fix the path |

## Code-API check

| Message | Cause | Fix |
|---|---|---|
| `the API check is switched off (PROBE_ENABLED is not true; ...)` | Off by default | See [SETUP_CODE_API_CHECK.md](SETUP_CODE_API_CHECK.md) |
| `not set: CODE_API_URL, PROBE_PHONE` | Missing settings | Set them |
| `NOT RUN: needs the PM's approval` | You did not approve | Run `python3 investigate.py --continue --approve-probe` |
| `CODE_API_URL must start with https:// ...` | Plain http | Use https |
| `PROBE_PHONE must be a number you own, with at least 10 digits` | Short number | Fix it |
| `CODE_API_TOKEN expired at ...` | Expired JWT | Put a fresh token in `.env` |
| `wait Ns before another API check ...` | Calls too close together | Wait `PROBE_MIN_GAP_S` seconds |
| `the API check already ran the maximum number of times in this session` | `PROBE_MAX_PER_RUN` reached | Start a new run, or raise it |
| `CODE_API_BODY_TEMPLATE is not valid JSON` | Bad JSON | Fix the quotes. The value must be one line |
| `result: auth_rejected` | 401 or 403 | Refresh `CODE_API_TOKEN`. This is not an outage |
| `result: no_answer` / `network_error` | Timeout / cannot connect | Raise `PROBE_TIMEOUT_S`, or check VPN and URL |
| `provider_log: Not seen yet ...` | The provider log lags | Not a fault. Check again later |

## Sessions, memory and files

| Message | Cause | Fix |
|---|---|---|
| `no saved investigations yet; start one with a question` | `--continue` or `--finish` with no session | Start with a question |
| `no session <id>; list them with --sessions` | Wrong id | Use `--sessions` |
| `a session id contains only letters, digits, underscore and dash` | Bad characters | Fix |
| `That investigation has no report yet.` | `--finish` before a report | Run the investigation first |
| `Not saved: outcome must be confirmed, probable, unresolved or discard.` | Bad `--outcome` | Use one of the four |
| `Not saved: the drafted case note is not valid (...)` | The model's note was bad | Try `--finish` again |
| `could not read a case note from the model; try again` | The model did not return JSON | Try again |
| `Cannot finish: ...` / `Cannot continue: ...` | A tool or model error. The text after it says why | Read it and use the matching row above |
| `Nothing new to add. Give --file and/or --note ...` | `--continue` with nothing | Add something, or accept that it will re-check the tools |
| Permission error on `.ii_secret` | The file exists with other owner | Set `SECRET_FILE` to a path you own, or delete the file (old session fingerprints will no longer match) |

If your problem is not here, run `python3 investigate.py --check --live` and read the result of each source.
