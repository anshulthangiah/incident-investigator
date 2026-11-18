# The code-API check

`check_code_api` is the only tool that does more than read. It calls your verification API once, with **your own test number**, and **sends one real message** to it. It uses a small amount of credit.

Use it when requests may be failing before they reach the delivery provider. Typical sign: the delivery logs show fewer requests but no new failures. A call to the API tells you whether the API answers, how fast, and whether the provider's log then shows the request.

The model passes no parameters to it. The URL, token and number all come from your settings.

## Safety rules built in

| Rule | How it is enforced |
|---|---|
| Off by default | `PROBE_ENABLED=false`. While it is not `true`, the tool is not offered to the model. |
| Needs your approval on every run | Either you add `--approve-probe`, or the tool asks `Approve this now? [y/N]` at the keyboard. It never auto-approves, and no approval is carried over from a saved session. If there is no keyboard (a script), the answer is no. |
| Your number only | `PROBE_PHONE` is the only number it ever uses. The model cannot choose one. The number is never printed or recorded. |
| Limits | At most `PROBE_MAX_PER_RUN` calls per session (default 2), at least `PROBE_MIN_GAP_S` seconds apart (default 15). |
| Safe URL | `CODE_API_URL` must start with `https://`. Plain `http://` is allowed only for localhost. |
| Token check | If `CODE_API_TOKEN` is a JWT that has expired, the tool stops and says when it expired. |
| Code never recorded | If the API response contains a code value, the value is not stored. The result gets a `SECURITY_FINDING` instead, because a code should never be returned to the caller. |

## Step 1: try it on the mock system first

The mock verification API is local and sends nothing.

```bash
PROBE_ENABLED=true python3 investigate.py --demo --mock-scenario S20 --approve-probe "users tap send verification code, the app spins and nothing arrives"
```

On Windows (PowerShell):

```powershell
$env:PROBE_ENABLED="true"
py -3 investigate.py --demo --mock-scenario S20 --approve-probe "users tap send verification code, the app spins and nothing arrives"
```

In the scenario S20 the mock API answers HTTP 500. The report shows `result: server_error`. Try `S18` (a slow API) or `S1a` too. Without `--approve-probe`, in a real terminal the tool asks you first.

## Step 2: settings for your real API

```text
PROBE_ENABLED=true
CODE_API_URL=https://api.example.test/v1/verify/start
CODE_API_TOKEN=<a bearer token, if the endpoint needs one>
PROBE_PHONE=<a number you own>
PROBE_COUNTRY_PREFIX=+99
PROBE_CLIENT=incident-probe
```

The default request body is JSON: `{"country_prefix": ..., "phone": ..., "client": ...}`, sent as a POST with `Authorization: Bearer <token>`. If your API expects other field names, set `CODE_API_BODY_TEMPLATE` to JSON text with placeholders `{country_prefix}`, `{phone}` and `{client}`:

```text
CODE_API_BODY_TEMPLATE={"prefix": "{country_prefix}", "mobile": "{phone}", "client_name": "{client}"}
```

`PROBE_PHONE` should be a number you own and can receive on. Use 10 or more digits. The tool uses the last 10 digits as the phone and `PROBE_COUNTRY_PREFIX` as the prefix.

All settings:

| Setting | Default | Meaning |
|---|---|---|
| `PROBE_ENABLED` | `false` | Master switch |
| `CODE_API_URL` | empty | The API endpoint |
| `CODE_API_TOKEN` | empty | Optional bearer token. Never printed. |
| `CODE_API_BODY_TEMPLATE` | empty | Optional JSON body with `{country_prefix}`, `{phone}`, `{client}` |
| `PROBE_PHONE` | `999000000001` | Your own test number |
| `PROBE_COUNTRY_PREFIX` | `+99` | Country prefix sent with it |
| `PROBE_CLIENT` | `incident-probe` | Client name sent with it |
| `PROBE_MAX_PER_RUN` | `2` | Calls per session |
| `PROBE_MIN_GAP_S` | `15` | Seconds between calls |
| `PROBE_TIMEOUT_S` | `30` | No answer within this is `no_answer` |
| `PROBE_SLOW_MS` | `5000` | Slower than this is `ok_but_slow` |
| `PROBE_LOG_WAIT_S` | `60` | How long to look for the request in the provider log |
| `PROBE_LOG_POLL_S` | `5` | Seconds between looks |
| `PROBE_EXPECT_TEXT` | `Request accepted` | Text the success message must contain |

Then check:

```bash
python3 investigate.py --check
```

The "Code API check" line must say ON, and must not list anything as "not set".

## Step 3: run it with approval

```bash
python3 investigate.py "users tap send and the app spins, nothing arrives" --approve-probe
```

If the model wants the check and you did not pass the flag, the tool asks. If the report says it needs the check, it will put this command in section 5: `python3 investigate.py --continue --approve-probe`.

## What it reports

| Field | Meaning |
|---|---|
| `result` | One of `ok`, `ok_but_slow`, `auth_rejected`, `server_error`, `request_rejected`, `unexpected_response`, `no_answer`, `network_error` |
| `http_status`, `elapsed_ms` | What came back and how long it took |
| `response_message` | The API's message, cut to 160 characters, credentials removed |
| `reading` | A plain sentence on what the result means and does not mean |
| `SECURITY_FINDING` | Present only if the response contained a code value |
| `provider_log` | After a success, whether the provider's log shows a request for your number |

## Why "not seen yet" is not a fault

After a success, the tool looks in the provider's live log (needs `PROVIDER_API_URL`, `PROVIDER_API_KEY` and `LOGS_SOURCE` set to `auto` or `api`) for a row for your number, for up to `PROBE_LOG_WAIT_S` seconds. The provider's log lags by seconds to minutes. If no row appears, the result says `row_seen: false` and "Not seen yet ... this is NOT a sign of a fault". Check again a few minutes later with `fetch_delivery_logs` or another API check before you suspect a break between your API and the provider. The model is told the same.

If the log source is not configured, `provider_log` says `checked: false` and why.

## What a healthy result does not prove

A healthy API now does not prove that the incident did not happen earlier. The check is about the API at this moment only.

If something goes wrong, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).
