# Changelog

All notable changes to this project, newest first. Problems fixed and still open are in [docs/KNOWN_ISSUES_AND_ROADMAP.md](docs/KNOWN_ISSUES_AND_ROADMAP.md). The GitHub Release for each version uses the same text.

## 1.0.0 - 2026-11-17

First public release. Mock-only: every provider, field name, error code, database and incident in this repository is invented.

### Added
- Delivery-log summary breaks failures down by route, sender, template and hour, and flags a concentration.
- Browser replay demo of five recorded runs (four recordings of the scripted stand-in and one of a real model), with a tour and Builder mode.
- The command-line tool `investigate.py`: a loop in which a language model picks read-only checks, reads each result, and writes a five-section report. Every claim carries an evidence tag (`[E#]` for a tool result, `[U#]` for something you told it). `inconclusive` is an allowed answer.
- Seven read-only tools: `fetch_delivery_logs`, `get_credit_balance`, `check_user_data`, `check_message_queue`, `check_numbers`, `check_code_api` and `recent_code_changes`. The model supplies dates only; it never supplies a URL, SQL, a path or a credential.
- A mock system to run it against: a mock messaging provider with a live log API (`GET /v1/logs`) and a credit call (`GET /v1/account/balance`), a mock verification API (`POST /v1/verify/start`), a SQLite database with accounts, sessions and an outbox, and two small git repositories. Generated with `python3 -m mock.generate --all`. Deterministic.
- Database checks for SQLite (run for real), SQL Server (`pymssql`) and Postgres (`psycopg`). The SQL Server and Postgres adapters are tested with fake drivers only. Fixed SELECT statements, aggregate counts only, read-only sessions, a read-replica flag with a lag estimate, timestamp-zone settings, and settings for object and column names.
- The code-API check, the only tool that does more than read. It sends one real test message to your own number. It is off by default and needs approval on every run (`--approve-probe` or a y/N prompt), with per-session and per-minute limits. A provider-log miss right after the call is reported as "not seen yet", not as a fault.
- An evaluation runner, `evals/run_evals.py`, with seven text-based checks per scenario and a `--scripted` mode.
- Real-model baseline: results for all 22 scenarios in evals/published/ and docs/EVALUATION_RESULTS.md. The evaluation runner has an optional --max-cost cap and saves each call's arguments and results.
- The scripted stand-in, `--demo`: fixed keyword rules and a template. It is not AI. Every output carries the banner `[SCRIPTED STAND-IN, NOT AI]`. It lets anyone run the full loop offline with no key.
- Two model adapters in the standard library: Anthropic, and an OpenAI-compatible adapter that serves OpenAI, xAI, Google's OpenAI-compatible endpoint, LM Studio, Ollama and similar through `LLM_BASE_URL`. A chat-app login token is refused with a clear message. Token use and an estimated cost are printed after every round.
- The continue loop: `--continue` with `--file`, `--note`, `--ask`, `--session`, and `--sessions` to list investigations. Added files are treated as untrusted data.
- Memory: `--finish` (with `--outcome`, `--cause`, `--yes`) saves a scrubbed case note only after you agree. `--knowledge` lists it. Built-in generic patterns are marked as leads, not conclusions.
- Specific numbers: `--number`, `--numbers-file`, `--prompt-numbers`. The model sees aliases `N1`, `N2` only. Saved files keep only keyed fingerprints (HMAC with a random per-install key in `.ii_secret`).
- Privacy features: redaction of keys and tokens from every output, scrubbing of sessions and reports, masking of emails, IP addresses and phone numbers in added files, message text never read, and a repository-wide test that scans every file for real-looking IP addresses, phone numbers and key-shaped strings.
- A preflight that tells the model which tools are off and why, and `--check [--live]` and `--tools-only [--date --days]` to look at the setup and the raw tool results without any model.
- Settings, all documented in `.env.example`: model, delivery logs, credit, repositories, database, queue facts, code-API check, limits, cost, `STATE_DIR`, `SECRET_FILE`, `REASON_GLOSSARY`, `LLM_TIMEOUT_S`, `LLM_TOKENS_PARAM`, `DB_PORT`, `DB_SSLMODE`, `DB_TDS_VERSION`, `DB_QCOL_*`, `CREDIT_PER_REQUEST`, `CODE_API_BODY_TEMPLATE`, `PROBE_*`, `MOCK_SCENARIO` and `MOCK_NOW`.
- Documentation: the README, and guides in `docs/` for the quick start, a language model, your own delivery provider, the database checks, the code-API check, privacy and safety, how it works, troubleshooting, known issues and roadmap, and developer build notes. `spec/SPEC.md` gained a section "Implementation status at v1.0.0".
- Tests: 211, run with `bash tests/run_phase1.sh` (about 60 seconds, standard library only).
- Scenarios S20 to S22, added after the first 19 (expected answers first, then the generator, then the lock). S20 is a verification API that answers a server error on save so nothing reaches the provider, S21 is a login that says the code is invalid because repeated requests replaced earlier codes, and S22 is stopped scheduled database jobs that no tool can see (expected outcome: inconclusive, ask the DBA). `expected.lock.json` has an entry for each.
- Scenarios S17 to S19, covering a bulk import with no dial code (S17), a hanging verification API (S18) and delayed but delivered messages (S19). S16 is intentionally unused.
- A user-data summary file for S17 (counts per creation date only, no user rows) and a test that every fault type used by a scenario is handled by the generator.
- The static browser demo in `demo/` (a scripted simulation with a guided tour and Builder mode), the product spec and the gaps document.

### Changed
- Evaluation scoring: required phrases also match plain paraphrases and the tool's template ids, and a verdict such as "no slowness found" now counts as finding nothing. Scenario S12 no longer requires a phrase that no tool shows, and its expected answer was re-locked.
- The scripted stand-in report uses plain bullet lines and finding-specific next steps.
- Scenarios S12, S14, S20 and S22: wording in the expected notes was edited and the expected answers were re-locked. The facts they check did not change.
- The default time zone for timestamps is UTC.
- The repository scan checks for real-looking IPs, phone numbers and key-shaped strings.

### Known limits at this release
- The scripted stand-in is rule-based, not AI. A scripted run of all 22 scenarios scores 115 of 154 checks. These scores are placeholders for the stand-in only and are not an AI score. It misses the `must_mention` check on many scenarios because its wording differs from the expected words (for example `replaced` against `replaces`). This is a stand-in limit.
- The real-model baseline is one run per scenario with one model. It is not an accuracy claim, and scenarios run twice moved. Details and caveats: [docs/EVALUATION_RESULTS.md](docs/EVALUATION_RESULTS.md).
- The SQL Server and Postgres adapters have not been run against a live server.
- Section-3 brevity and the report length aim are enforced only by the prompt.
