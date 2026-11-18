# Current state and gaps

## Purpose

A project to explore how a language model can help a product manager look into a vague report such as "verification codes are not arriving". The model picks read-only checks, reads each result and writes a short report in which every claim points to the evidence behind it. "Inconclusive" is an allowed answer.

This is a portfolio project. It runs only against an invented system. Nothing here claims real users, real incidents or research findings.

## What is built

- A command-line tool, `investigate.py`, with seven read-only tools: delivery logs, credit balance, user data, message queue, number check, code-API check and recent code changes.
- A mock system to run it against: a fake messaging provider (log API and credit call), a fake verification API, a SQLite database and two small git repositories.
- 22 invented scenarios with expected answers, and an evaluation runner with text-based checks, and one published real-model baseline.
- A scripted stand-in (`--demo`) that runs the whole loop offline. It is rule-based, not AI.
- Privacy features: redaction of keys and tokens, masking of numbers, and repository-wide scan tests.
- A static browser demo in `demo/` with a guided tour.

## What is not built

- There is no accuracy figure. A real-model baseline is published (`claude-sonnet-5-5`, 129 of 154 checks, one run per scenario, invented data), with its limits, in [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md).
- The SQL Server and Postgres adapters have been run only with fake drivers.
- No claim verifier: the tool checks that cited tags exist, not that a number matches its source.
- Only one provider shape (the mock's) is supported without a small adapter.
- No web interface, no sub-agents, and no checks on causes that only a server can show (the API server's own log, the database scheduler).
- Report brevity and length are enforced only by the prompt.

The full list, with what each item means for you, is in [KNOWN_ISSUES_AND_ROADMAP.md](KNOWN_ISSUES_AND_ROADMAP.md).
