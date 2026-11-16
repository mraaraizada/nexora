# NEXORA — Connected Publishing Infrastructure

**One API. Multiple Platforms. Connected Publishing.**

NEXORA accepts a single short message (containing exactly one CTA link) and publishes
it to multiple third-party platforms through their official APIs — concurrently,
independently, and with an honest, per-platform result for each one. Built as a
timed Python practical test (FastAPI backend engineering).

## Objectives

- One request → many integrations → independent publishing → one unified result.
- Platform selection is entirely internal — the caller never specifies platforms.
- A failure on one platform must never stop the others, and must never be hidden or faked.

## Key Features

- `POST /posting` — validated input (message length, exactly-one-CTA-URL), internal platform fan-out.
- Five real platform integrations: Telegram, Mastodon, Write.as, Dev.to, Bluesky (see `docs/platform_research.md`).
- Fully concurrent, isolated publishing via `asyncio.gather` — one platform's exception or failure never affects the others.
- Honest, specific failure reporting: missing credentials, auth failure, rate limiting, timeout, and network errors are each reported distinctly, never silently skipped or faked as success.
- Interactive Swagger docs at `/docs`.
- 34 automated tests (`pytest`), all external HTTP mocked — no network calls during the test suite.

## Technology Stack

Python 3.11, FastAPI, Uvicorn, Pydantic v2, HTTPX (async), python-dotenv, pytest + pytest-asyncio + respx (test mocking).

## System Architecture

Modular, adapter-based:

- **`app/schemas.py`** — Pydantic request/response models; the message's length and single-CTA-URL rules are enforced here via a field validator, independent of the publishing logic.
- **`app/utils/url_validator.py`** — pure, dependency-free CTA URL extraction/validation logic, reused by both the schema and the standalone validation service.
- **`app/services/validation_service.py`** — the same validation, callable without FastAPI/pydantic (for direct testing/reuse).
- **`app/platforms/base.py`** — the `PlatformAdapter` abstract interface + a shared `publish()` template method that standardizes success/failure handling, timestamps, and error classification (auth/rate-limit/timeout/network) across every adapter.
- **`app/platforms/{telegram,mastodon,writeas,devto,bluesky}.py`** — one adapter per platform; each owns its own request construction, auth, and response parsing. No platform-specific logic lives in the route or orchestrator.
- **`app/services/posting_service.py`** — the platform registry (the one place "which platforms" is decided) and the concurrent orchestration (`asyncio.gather`, with per-adapter exception isolation as a last-resort safety net on top of each adapter's own error handling).
- **`app/services/result_service.py`** — aggregates individual `PlatformResult`s into the final response, computing `success` (true only if every platform succeeded).
- **`app/api/routes.py`** / **`app/main.py`** — the thin FastAPI route and app setup; a custom validation-error handler flattens pydantic's error shape into a readable `{field, message}` list.

## Directory Structure

```text
nexora/
├── app/
│   ├── main.py                 # FastAPI app, exception handlers
│   ├── config.py               # Environment-based settings (all optional, degrade gracefully)
│   ├── schemas.py               # Request/response models + input validation
│   ├── api/
│   │   └── routes.py            # POST /posting
│   ├── platforms/
│   │   ├── base.py              # Adapter interface + shared publish() template
│   │   ├── telegram.py
│   │   ├── mastodon.py
│   │   ├── writeas.py
│   │   ├── devto.py
│   │   └── bluesky.py
│   ├── services/
│   │   ├── posting_service.py    # Platform registry + concurrent orchestration
│   │   ├── validation_service.py
│   │   └── result_service.py
│   └── utils/
│       ├── url_validator.py
│       └── time_utils.py
├── tests/
│   ├── test_validation.py
│   ├── test_platforms.py
│   └── test_posting.py
├── docs/
│   └── platform_research.md
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

## Platform Integration Details

See [`docs/platform_research.md`](docs/platform_research.md) for the full research:
each platform's real API endpoint, auth scheme, official docs link, and why it was
chosen (or, for two considered-and-rejected platforms, why it wasn't).

## Prerequisites

- Python 3.10+ (developed and tested on 3.11)

## Installation

```bash
git clone <repo-url> nexora && cd nexora
python -m venv .venv
.venv\Scripts\activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
```

## Environment Configuration

Every variable is optional — a platform with missing credentials reports a clean
`"failed"` result with a specific `"Not configured: ..."` error instead of crashing the
application or the request. See `.env.example` for the full list and where to obtain
each value (Telegram bot token via @BotFather, Mastodon app token via your instance's
Settings → Development, Write.as needs nothing, a Dev.to API key, a Bluesky app password).

**Never commit a filled-in `.env`** — it's already gitignored.

## Platform Account Setup (summary — see `.env.example` for direct links)

| Platform | What you need |
|---|---|
| Telegram | A bot via `@BotFather`, added as an admin to the target channel/chat |
| Mastodon | An application access token from any instance (e.g. mastodon.social) |
| Write.as | Nothing — anonymous posting works with zero setup (optional access token to attribute posts to an account) |
| Dev.to | An API key from your Dev.to account settings |
| Bluesky | A handle + an **app password** (not your real account password) |

## Running the Server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000
```

## Swagger Documentation

Once running: **http://localhost:4000/docs**

## API Request Example

```bash
curl -X POST http://localhost:4000/posting \
  -H "Content-Type: application/json" \
  -d '{"message": "Check out our latest business platform and grow your online visibility. https://example.com"}'
```

## API Response Example

This is the **real, actual response** captured from this implementation (no platforms
configured in this environment, except Write.as which needs none — see Known Limitations):

```json
{
  "success": false,
  "results": [
    {"platform": "Telegram", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "Not configured: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required"},
    {"platform": "Mastodon", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "Not configured: MASTODON_ACCESS_TOKEN (and MASTODON_INSTANCE_URL) are required"},
    {"platform": "Write.as", "status": "success", "posted_url": "https://write.as/<id>", "public_access": true, "date": "2026-11-16", "time": "...", "error": null},
    {"platform": "Dev.to", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "Not configured: DEVTO_API_KEY is required"},
    {"platform": "Bluesky", "status": "failed", "posted_url": null, "public_access": false, "date": null, "time": null, "error": "Not configured: BLUESKY_HANDLE and BLUESKY_APP_PASSWORD are required"}
  ]
}
```

(Write.as's success case above is real — confirmed with one live anonymous post during
development; the exact `id`/timestamp are redacted here since that was a one-off test
post, not something to republish verbatim, but the shape and `status: "success"` are genuine.)

With real credentials configured, a successful platform's entry instead looks like
(**illustrative shape only, not a real captured value** — see the original spec's own
example for the same caveat):

```json
{"platform": "Mastodon", "status": "success", "posted_url": "https://mastodon.social/@you/112233445566778899", "public_access": true, "date": "2026-11-16", "time": "10:30:00", "error": null}
```

## Automated Testing

```bash
pytest -q
```

34 tests covering:
- **Input validation** — valid message, empty, >200 chars, missing CTA, multiple CTAs, invalid URL scheme, scheme-less "URL".
- **Platform integration** (mocked HTTP, per adapter) — success, auth failure, rate limiting, timeout, network failure, malformed response.
- **Orchestration** — all succeed, one fails, multiple fail, all fail, not-configured platforms never crash the request, and the real FastAPI route's validation responses (422s) and Swagger/OpenAPI availability.

All external HTTP calls in the test suite are mocked with `respx` — no real network
calls are made while testing.

## Security Considerations

- No secrets committed: `.env` is gitignored; only `.env.example` (names, no values) is tracked.
- Every credential is read from environment variables, never hardcoded.
- A missing credential degrades that one platform to a clean failure, never a crash or a silent skip.
- Errors returned to the client are specific but not leaky: HTTP error bodies are surfaced for debugging, but generic categories (auth failure, rate limit, timeout, network error) are used where a raw platform error could be noisy or inconsistent in shape.
- Per-request timeout (`NEXORA_REQUEST_TIMEOUT`, default 10s) on every outbound call — no request can hang indefinitely.
- No uncontrolled retries — each platform is attempted exactly once per request, so a transient failure is reported honestly rather than silently retried into a duplicate post.

## Known Limitations

- **No live credential verification for 4 of 5 platforms.** This was built in an environment with no real accounts/API keys for Telegram, Mastodon, Dev.to, or Bluesky. Every adapter is implemented against each platform's real, documented API contract and is covered by tests using mocked HTTP responses, but only Write.as (which needs no credentials) has been exercised end-to-end against a live account. See `docs/platform_research.md` for the full honesty note on this.
- **Telegram's permalink requires a public channel username.** Posting to a private group/chat still succeeds, but there's no equivalent public URL to report — the adapter returns a non-public `telegram://` reference instead of guessing a URL.
- **No retry/backoff on rate limiting.** A 429 is reported as a clean failure rather than automatically retried, by design (per the "avoid uncontrolled retries" requirement) — a caller can choose to retry the whole request later.
- **No persistence layer.** Each request is stateless; there's no database of past posts, no deduplication across requests, and no history endpoint — out of scope for this practical test.

## Future Improvements

- Optional retry-with-backoff, configurable per platform, with idempotency protection against duplicate posts.
- A lightweight persistence layer (e.g. SQLite) to record post history and allow a `GET /posting/history` endpoint.
- Image/media attachment support (all five chosen platforms support it in their real APIs; this test's scope was text + one link).
- Structured logging with credential redaction for production observability.
- Live integration tests (opt-in, real network, run manually against real test accounts) alongside the existing fully-mocked unit/integration suite.
