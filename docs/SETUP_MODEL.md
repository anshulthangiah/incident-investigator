# Connect a language model

The scripted `--demo` needs no model. To get real reasoning you need a model service and a key. The tool talks to two kinds of service, set by `LLM_PROVIDER`.

Copy the settings file first:

macOS or Linux:

```bash
cp .env.example .env
```

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

`.env` is git-ignored. If there is no `.env`, the tool reads `.env.example` instead. Real environment variables win over both.

**Important:** `.env.example` contains `MOCK_SCENARIO=S19`. While that line is active, every run starts the local mock system and points all settings at it. For a first model run on mock data, leave it. To use your own systems later, comment it out (see [SETUP_REAL_SYSTEM.md](SETUP_REAL_SYSTEM.md)).

## Option 1: Anthropic

In `.env`:

```text
LLM_PROVIDER=anthropic
LLM_API_KEY=<your API key>
LLM_MODEL=<the model name Anthropic documents>
```

Leave `LLM_BASE_URL` empty. The tool calls `https://api.anthropic.com/v1/messages`.

**A chat-app login token is refused.** A value that starts with `sk-ant-oat` is a login token from a chat app. The API does not accept it, and the tool stops with a message. Create an API key in the provider's console (it starts with `sk-ant-api`) and put that in `LLM_API_KEY`.

## Option 2: OpenAI-compatible services

One code path serves every service that speaks the Chat Completions format. Set `LLM_PROVIDER=openai_compatible` and choose the service with `LLM_BASE_URL`. If `LLM_BASE_URL` is empty, `https://api.openai.com/v1` is used.

| Service | `LLM_BASE_URL` | Key |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` (or leave empty) | Required |
| LM Studio (local) | `http://localhost:1234/v1` | Not needed on localhost |
| Ollama (local) | `http://localhost:11434/v1` | Not needed on localhost |
| xAI | the base URL xAI documents for its OpenAI-compatible API | Required |
| Google's OpenAI-compatible endpoint | the base URL Google documents for it | Required |

The code names these services in `investigator/llm.py`. Only the first three URLs appear in the repository (`.env.example` and the code). For xAI and Google, copy the current base URL from the provider's own documentation. They are not tested here.

Rules enforced by the code:

- The URL must start with `https://`. Plain `http://` is allowed only for `localhost`, `127.0.0.1` and `::1`.
- A key is required unless the URL is on localhost.
- Some services want `max_completion_tokens` instead of `max_tokens`. Set `LLM_TOKENS_PARAM=max_completion_tokens` for those.
- The model must support tool calling. Small local models often call tools badly. Expect weaker reports.

Example for a local Ollama:

```text
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=<a model you have pulled that supports tools>
LLM_API_KEY=
```

## Check it

```bash
python3 investigate.py --check
```

The Language model line must say `key set` and `model` with a name (the values are never printed). Then run a first investigation on mock data:

```bash
python3 investigate.py "users say verification codes arrive after they expire"
```

## Cost

Every round makes several model calls (one per tool step, at most `MAX_STEPS`). The tool prints the tokens used and an estimated cost after each round. The estimate is only as good as the two price settings, which you must fill in from your provider's price page:

| Setting | Default | Meaning |
|---|---|---|
| `PRICE_IN_PER_MTOK` | `2` | Price per million input tokens |
| `PRICE_OUT_PER_MTOK` | `10` | Price per million output tokens |
| `MAX_STEPS` | `12` | Tool-calling steps per round |
| `MAX_SECONDS` | `120` | Seconds per round |
| `MAX_OUTPUT_TOKENS` | `8000` | A report that reaches this is flagged as cut off |
| `LLM_TIMEOUT_S` | `120` | Seconds to wait for one model call |

The defaults for the two prices are placeholders, not your provider's prices. Check the provider's usage page for the real bill.

## Start with a small budget

- Set a spending cap in your provider's console before the first run.
- Use a cheap model first. Run one scenario on mock data: `python3 evals/run_evals.py --scenarios S21`.
- Lower `MAX_STEPS` (for example to `6`) for the first runs.
- Do not run `python3 evals/run_evals.py` without `--scenarios` on a real model until you know the cost of one scenario. It runs all 22 and spends money on each. The tool says so before it starts.
- Pass `--max-cost` (US dollars) to cap an evaluation. It is optional and there is no default cap.
- `--finish` makes one more model call to write the case note. `--demo` and `--tools-only` never call a model.

## Run the evaluation with your own model

A real-model baseline is published in [EVALUATION_RESULTS.md](EVALUATION_RESULTS.md). To get numbers for your own model:

1. Create `.env` (git-ignored) with `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `PRICE_IN_PER_MTOK` and `PRICE_OUT_PER_MTOK`.
2. Generate the mock data: `python3 -m mock.generate --all`.
3. Run one scenario: `python3 evals/run_evals.py --scenarios S2 --max-cost 1.00`.
4. Check the spend it prints and your provider's usage page. Then run more scenarios.

`--max-cost` is optional. Without it the runner has no limit, and it still prints the estimated spend. With it, the runner stops before any call whose worst case would pass the cap. To stop early, press Ctrl+C. With the model used for the baseline, one scenario cost about 5 to 8 US cents; yours will differ. Results go to `evals/results/` (git-ignored) and include each call's arguments and results.

## What leaves your computer

The model receives your question, the tool results (counts, rates, timings, masked text), and your notes after masking. It never receives phone numbers, credentials or database rows. Details: [PRIVACY_AND_SAFETY.md](PRIVACY_AND_SAFETY.md). Check the terms of the model service before sending anything sensitive to a hosted model.
