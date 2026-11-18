# Database checks

Two tools read a database: `check_user_data` (accounts created per day, and how many have an empty language or an empty country prefix) and `check_message_queue` (how many outgoing messages are pending, and for how long). `check_numbers` also reads one account record per number you supply.

They are off until you set `DB_ENABLED=true`.

## What they read, and what they never read

| Tool | Reads | Returns |
|---|---|---|
| `check_user_data` | The accounts table: created time, language, country prefix | Per day: `new_users`, `locale_empty` (accounts with an empty language), `dial_code_empty` (accounts with an empty country prefix) (counts) |
| `check_message_queue` | The outbox table: channel, status, created time, updated time | Counts per channel and status, ages, and how long sent rows waited (buckets: under 30 s, 30 s to 2 min, 2 to 10 min, 10 to 30 min, over 30 min) |
| `check_numbers` | Accounts table, and the sessions table if set: login reference (the number, as a parameter), flags, timestamps | Per number: record count, flags, timestamps, and that account's own session records |

The tool never reads names, email addresses, phone numbers (except as a lookup parameter you gave), tokens, message bodies or destinations, and never returns a user row. Every statement is a fixed SELECT with the dates passed as parameters. The model chooses dates only. A last-line check (`assert_select` in `investigator/db.py`) refuses anything that is not a single SELECT.

## Which databases

| `DB_KIND` | Driver | Status in v1.0.0 |
|---|---|---|
| `sqlite` (default) | Built into Python | Runs for real (the mock system uses it) |
| `mssql` | `pymssql` (optional) | Tested with a fake driver only |
| `postgres` (also `postgresql`, `pg`) | `psycopg` (optional) | Tested with a fake driver only |

Be honest with yourself about the last two: they have not been run against a live server by the author. Start with a test database, and read [KNOWN_ISSUES_AND_ROADMAP.md](KNOWN_ISSUES_AND_ROADMAP.md).

## Install a driver (only for SQL Server or Postgres)

Use a virtual environment.

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pymssql              # SQL Server
pip install "psycopg[binary]"    # Postgres
```

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install pymssql
pip install "psycopg[binary]"
```

If the driver is missing the tool says so: `pymssql is not installed (pip install pymssql); it is optional and used only for DB_KIND=mssql`.

## Ask your DBA for a safe login

Do not use an administrator or application login. Ask the database administrator for:

1. A new login that can only `SELECT`. No insert, update, delete or execute rights.
2. Access to **views**, not tables. The views should expose only the columns the tool reads (listed below) and nothing else. Name them whatever you like and set `DB_USERS_OBJECT`, `DB_DEVICES_OBJECT` and `DB_QUEUE_OBJECT`.
3. If possible, a connection to a **read replica**, so your checks cannot slow the live database. Then set `DB_REPLICA=true`.
4. A network route (VPN or allow-list) from your machine.

Columns the tool reads, with default names:

| Object | Column | Setting to rename it | Default |
|---|---|---|---|
| accounts | account id | `DB_COL_USER_ID` | `id` |
| accounts | login reference (the national phone number) | `DB_COL_USERNAME` | `login_ref` |
| accounts | language | `DB_COL_LOCALE` | `language` |
| accounts | country prefix | `DB_COL_DIAL_CODE` | `country_prefix` |
| accounts | active flag | `DB_COL_ACTIVE` | `is_active` |
| accounts | phone verified flag | `DB_COL_PHONE_CONFIRMED` | `phone_verified` |
| accounts | created time | `DB_COL_CREATED` | `created_at` |
| accounts | updated time | `DB_COL_UPDATED` | `updated_at` |
| sessions | account id | `DB_COL_DEV_USERID` | `account_id` |
| sessions | code valid until | `DB_COL_DEV_CODE_EXPIRY` | `code_valid_until` |
| sessions | last seen time | `DB_COL_DEV_LOGIN` | `last_seen_at` |
| outbox | channel | `DB_QCOL_CHANNEL` | `kind` |
| outbox | status | `DB_QCOL_STATUS` | `state` |
| outbox | created time | `DB_QCOL_CREATED` | `created_at` |
| outbox | updated time | `DB_QCOL_UPDATED` | `updated_at` |

Column settings take plain names only (letters, digits, underscore). The outbox statuses the tool knows are `PENDING`, `SENDING`, `SENT`, `FAILED`, `ON_HOLD`, `BLOCKED`; the mock outbox uses `PENDING`, `SENDING`, `SENT` and `ON_HOLD`. Anything else is listed under `unusual_statuses_in_window`. The mock outbox table has the columns `id`, `kind`, `state`, `created_at`, `updated_at`, `body` and `destination`; the tool never reads `body` or `destination`.

## Settings

SQLite on the mock data (this is what the mock system sets for you):

```text
DB_ENABLED=true
DB_KIND=sqlite
DB_NAME=mock/generated/S19/mock.db
```

SQL Server:

```text
DB_ENABLED=true
DB_KIND=mssql
DB_HOST=203.0.113.5,1433
DB_NAME=appdb
DB_USER=investigator_ro
DB_PASSWORD=<password>
DB_TIMESTAMP_TZ=UTC
DB_USERS_OBJECT=reporting.v_accounts
DB_QUEUE_OBJECT=reporting.v_outbox
DB_DEVICES_OBJECT=reporting.v_sessions
```

Postgres:

```text
DB_ENABLED=true
DB_KIND=postgres
DB_HOST=db.example.com:5432
DB_NAME=appdb
DB_USER=investigator_ro
DB_PASSWORD=<password>
DB_SSLMODE=require
DB_USERS_OBJECT=public.v_accounts
DB_QUEUE_OBJECT=public.v_outbox
DB_DEVICES_OBJECT=public.v_sessions
```

Notes:

- `DB_HOST` is a host name or address, optionally with a port after `,` or `:`. `DB_PORT` is an alternative way to give the port. Defaults: 1433 for SQL Server, 5432 for Postgres.
- Object names must be plain, such as `accounts` or `reporting.v_accounts`. SQL Server also allows `[bracketed]` names and up to three parts. Postgres allows `"Quoted"` names and up to two parts. Host and database name go in `DB_HOST` and `DB_NAME`, not in the object name. Defaults when empty: `accounts`, `sessions`, `outbox` (SQLite and SQL Server), `public.accounts`, `public.sessions`, `public.outbox` (Postgres).
- Set `DB_DEVICES_OBJECT=none` to switch the session lookup off.
- For SQLite, `DB_NAME` is the file path, opened read-only.
- Sessions are read-only where the database supports it. For Postgres the tool sets `default_transaction_read_only=on` and a 30-second statement timeout. The SQL Server login and query timeouts are 15 and 30 seconds.

## Timestamp zone

The tool compares stored timestamps with UTC dates. Tell it which zone your columns store:

| Setting | Values | Meaning |
|---|---|---|
| `DB_TIMESTAMP_TZ` | `UTC` (default; the only accepted value) | Zone of all stored timestamps (accounts, sessions and outbox) |

A wrong value shifts every day boundary and every wait time. Ask the DBA.

## Read replica and lag

If your connection goes to a replica, set `DB_REPLICA=true`. The tool then adds a warning to its results: counts may trail the live database by seconds to minutes. It also estimates the lag from the newest account record (`freshest_signup_minutes_ago`). That is an upper bound only when sign-ups are frequent. With a replica, the model is told not to call anything healthy on the strength of that data alone.

## Queue facts

The queue tool estimates how long the queue would take to clear using three facts about your system. Set them to the values of your own system:

| Setting | Default | Meaning |
|---|---|---|
| `QUEUE_BATCH_SIZE` | `20` | Rows the worker takes per channel per tick |
| `QUEUE_TICK_S` | `30` | Seconds between ticks |
| `CODE_EXPIRY_MIN` | `10` | Minutes a code stays valid |

The estimate is labelled "mock defaults" and `estimate_basis` states the batch size and tick used. The actual rate may be lower. Rows still `PENDING` after more than `CODE_EXPIRY_MIN` minutes are counted in `older_than_<N>_min` (for example `older_than_10_min`) and reported in `reading`.

The wait result (`wait_before_sent`, per channel) has the fields `sent_rows`, `under_30_s`, `30_s_to_2_min`, `2_to_10_min`, `10_to_30_min`, and `over_30_min`. Wait is the last-update time minus the created time for `SENT` rows.

## Old SQL Server and TLS

Old SQL Servers may need an older protocol version. Set `DB_TDS_VERSION` to the value `pymssql` accepts, for example `7.3` (leave empty otherwise). If you get a connection error that mentions TLS or the handshake, ask your DBA which protocol version and encryption the server requires, then try `DB_TDS_VERSION`. The tool cannot turn encryption off for you. For Postgres, use `DB_SSLMODE` (`prefer` by default, `require` for a managed server).

## Check

```bash
python3 investigate.py --check
python3 investigate.py --check --live
```

The "Database checks" line shows ON or off, the kind, the zone and whether it is a replica. In the "Tools right now" line, `check_user_data` and `check_message_queue` must not say `off`. `--check` opens a socket to the server for 3 seconds to test reachability. `--check --live` runs both tools for today.

Errors are rewritten into short sentences with no host, user or password in them. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

## Limits to remember

- The tools read the data as it is **now**. Records edited by hand later can hide earlier problems; counts here are current, not historical.
- `SENT` in the queue means the worker handed the row to the provider. It does not mean the user received it.
- The queue tool cannot tell verification-code rows from other messages. It never reads the message body.
- If the newest row in the outbox table is older than the window you asked about, the tool sets `newest_row_recent` to false. Do not read an empty or old queue as healthy in that case.
