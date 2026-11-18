# Connect your own delivery provider

This guide connects the tool to a real messaging provider that sends your verification codes. Read [PRIVACY_AND_SAFETY.md](PRIVACY_AND_SAFETY.md) first. Do this with the owner of the provider account.

The tool was built against an invented provider. Your provider will differ in field names and in the shape of its API. Part of this guide is therefore "map your data to what the tool expects". The CSV route needs no code change. The live-API route may need a small adapter (see [Live API](#route-b-live-log-api)).

## Checklist

Tick each line before you run a real investigation.

- [ ] I have permission to read the provider's delivery logs and to use them with this tool.
- [ ] I have a delivery-log source: CSV exports (route A) or a log API with a read-only key (route B).
- [ ] Exports are in UTC, or I know the zone and will convert (see [Time zone](#time-zone)).
- [ ] Exports do not contain message text, or I have removed that column (see [What not to export](#what-not-to-export)).
- [ ] The export folder is outside any git repository, or git-ignored.
- [ ] I replaced `data/reason_glossary.json` with my provider's own failure reasons.
- [ ] I commented out `MOCK_SCENARIO` in `.env`.
- [ ] `python3 investigate.py --check` shows my sources, and `--check --live` works.
- [ ] I ran `python3 investigate.py --tools-only --days 3` and the numbers match the provider console.
- [ ] I set `CREDIT_URL` if my provider has a balance call (optional).
- [ ] I set `REPO_PATHS` to local clones of the repositories I want checked (optional).

## Step 1: make your own settings file

macOS or Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Open `.env` in a text editor. Put `#` in front of this line so the mock system is not started:

```text
# MOCK_SCENARIO=S19
```

If you leave `MOCK_SCENARIO` active, every run overrides your settings with the mock ones. `--check` prints a line starting `(mock stack for scenario ...` when this happens.

## Step 2: choose how logs arrive

`LOGS_SOURCE` has three values:

| Value | Behaviour |
|---|---|
| `auto` (default) | Dates in the last 7 days come from the live API, if `PROVIDER_API_URL` and `PROVIDER_API_KEY` are set. Older dates come from CSV files. If the API call fails, those days are read from CSV and a note says so. |
| `csv` | Only CSV files in `LOGS_DIR`. |
| `api` | Only the live API. It serves at most the last 7 days; an older date stops with an error. |

## Route A: CSV exports (no code change)

Use this first. It works with any provider that lets you export a delivery report.

### What the file must look like

`fetch_delivery_logs` reads every `*.csv` file under `LOGS_DIR` (default `data/exports`, searched in sub-folders too). A file counts as a delivery export if its header row contains `sent_at` and `status`. The tool reads these columns:

| Column | Used for | Format |
|---|---|---|
| `sent_at` | When the request was made | `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD HH:MM`, or an ISO timestamp. Without a zone it is read as UTC. |
| `status` | `Delivered` counts as delivered. Anything else counts as failed. | Text, case-insensitive |
| `failure` | Reason for a failed row | Text, matched against the glossary |
| `delivered_on` and `delivered_at` | When it was delivered, for the delay figures | `YYYY-MM-DD` and `HH:MM:SS` |
| `template` | Per-template counts | Text |
| `request_ref` | Removes the same request when exports overlap | Text |
| `to` | Distinct recipients, repeat requests, number-shape counts (only as a fingerprint) | Digits |

The mock export has these 17 columns, in this order. Your export may have different names. Rename the header row to match, or ask your provider for a custom report.

```text
sent_at, template, status, delivered_on, delivered_at, request_ref, to, country, cost,
sender, registration_ref, channel, body, route, failure, length, client_ip
```

Only the eight columns in the table above are read. The others (`country`, `cost`, `sender`, `registration_ref`, `channel`, `body`, `route`, `length`, `client_ip`) are ignored. You do not need to export them. Leave them out.

### What not to export

- **Message text (`body`).** In real providers it holds the code itself and often a name. The tool never reads it, but the file sits on your disk. Leave this column out of the export. If you cannot, delete the column before you save the file in `LOGS_DIR`.
- Client IP addresses and sender details you do not need.
- Do not open the CSV in a spreadsheet and save it again. A spreadsheet rewrites long numbers as `9.99E+11`. The tool detects this, reports it as `data_quality`, and tells you the number checks are unreliable. Export straight to CSV.

### Where to put the files, and keep them out of git

```bash
mkdir -p data/exports
cp ~/Downloads/delivery_report_2026-11-16.csv data/exports/
```

`data/exports/` is already in `.gitignore`. If you use another folder, set `LOGS_DIR=/path/to/folder` and keep it outside the repository.

You can also add a file while investigating: `python3 investigate.py --continue --file path/to/export.csv`. The tool copies it into `LOGS_DIR` and prints how many rows and days it covers. A file larger than 25 MB is refused; export a shorter period.

### The failed-call log (optional)

Some providers refuse a request before it is submitted (for example when credit runs out). Those requests have no delivery row. If your provider exports a "failed calls" log, put it in `LOGS_DIR` too. The tool recognises a file whose header has `ref` and `code`, and uses `at`. The mock layout is:

```text
ref, at, sender, ip, to, text, code, reason
```

Only `ref`, `at` and `code` are read. Error codes are explained from the `error_codes` section of the glossary.

### Time zone

All dates are UTC. A timestamp with no zone is read as UTC. A timestamp with an offset (`+00:00`, `Z`) is converted to UTC. If your export is in another zone without an offset, add the offset to the column before you use it. The tool has no setting for the zone of CSV files.

## Route B: live log API

The live route is read-only and fetches the last 7 days. The tool expects the shape of the mock server (`mock/api_server.py`):

| Item | What the tool sends or expects |
|---|---|
| Base URL | `PROVIDER_API_URL` (https; plain http only for localhost) |
| Request | `GET {PROVIDER_API_URL}/v1/logs?date=YYYY-MM-DD` (one call per day) |
| Auth header | `Authorization: Bearer <PROVIDER_API_KEY>` |
| Response | JSON: `{"data": [row, ...], "metadata": {"total": n}}` |
| Row fields read | `sent_at`, `status`, `failure`, `delivered_at`, `template`, `request_ref`, `to` |
| Timestamps | ISO (`2026-11-16T11:59:35+00:00`) or `YYYY-MM-DD HH:MM:SS` (read as UTC) |
| Completeness | If `metadata.total` differs from the number of rows returned, the tool marks that day INCOMPLETE |
| Duplicates | Rows with the same `request_ref` count once |

If your provider's API looks different (another path, another auth header, a `page` parameter, other field names), change two small functions in `investigator/tools.py`:

- `_api_get(path, params)` builds the request. Change the path, the headers and the paging there.
- `_norm_api(r)` maps one row of your API response to the tool's row. Change the field names there.

Keep the request read-only. Run the tests afterwards (`bash tests/run_phase1.sh`). See [BUILD_NOTES.md](BUILD_NOTES.md#add-a-provider).

Settings for route B:

```text
LOGS_SOURCE=auto
PROVIDER_API_URL=https://logs.your-provider.example
PROVIDER_API_KEY=<a read-only key>
```

Use a key that can read logs and cannot send messages, if your provider offers one. The key is never printed.

## Step 3: replace the failure-reason glossary

The tool explains failure reasons in plain words from `data/reason_glossary.json`. The shipped file holds invented wording for the mock provider. A reason that is not in the file is reported as "not documented". It is never guessed. That is on purpose.

1. Get your provider's own documented list of failure reasons.
2. Open `data/reason_glossary.json`. Keep the `categories` section and edit it if you need new categories (each has `label` and `who_fixes`).
3. Replace the `reasons` list. Each entry looks like this:

```json
{"match": ["recipient unreachable"], "label": "Recipient unreachable",
 "category": "recipient_device",
 "meaning": "The provider could not reach the recipient's phone."}
```

`match` is a list of lower-case phrases. An entry matches when any phrase is found inside the reason text (case and trailing full stops ignored). `category` must be a key of `categories`.
4. Replace `error_codes` with your provider's pre-submission codes, or empty it (`{}`).
5. To keep your glossary outside the repository, set `REASON_GLOSSARY=/path/to/your_glossary.json`.

Do not paste real customer data into the glossary.

## Step 4: credit balance (optional)

If your provider has a balance call, it must look like this: a `GET` to `CREDIT_URL` with no query parameters, the key sent in a request header, and a reply that is either a JSON object such as `{"balance": 12.5, "units": "credits"}` or a bare number.

```text
CREDIT_URL=https://api.your-provider.example/balance
PROVIDER_API_KEY=<key>
CREDIT_KEY_HEADER=X-Api-Key
CREDIT_PER_REQUEST=0.05
```

The tool sends `PROVIDER_API_KEY` in the header named by `CREDIT_KEY_HEADER` (default `X-Api-Key`). The body must be a plain number or a JSON object with a `balance` number. `CREDIT_PER_REQUEST` is used to compute "requests remaining". If your provider's call has a different shape (another auth scheme, query parameters, another field name), it needs a small change to `get_credit_balance()` in `investigator/tools.py`.

## Step 5: code repositories (optional)

```text
REPO_PATHS=/path/to/code_service,/path/to/message_gateway
```

Comma-separated paths of local git clones. The tool runs `git log` and returns commit hashes, dates, authors, subjects and file names, at most 30 commits per repository. It never reads code.

## Step 6: check

```bash
python3 investigate.py --check
python3 investigate.py --check --live
python3 investigate.py --tools-only --days 3
```

`--check` lists each source as set or not set. `--check --live` makes one real call per source. `--tools-only` prints the raw results. Compare them with your provider's console for the same dates. If they do not match, stop and fix this before you ask the model anything.

Then connect a model ([SETUP_MODEL.md](SETUP_MODEL.md)) and, if you want the database checks, [SETUP_DATABASE.md](SETUP_DATABASE.md).

If something fails, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
