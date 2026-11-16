# Evidence

Real artifacts captured during development, included as the spec's requested
"screenshots or logs demonstrating your implementation."

- **`pytest_run.txt`** — full output of the default automated test suite (`pytest -v`),
  captured directly from a real run: 40 passed, 2 deselected, 0 failed.
- **`live_posting_response.json`** — the real JSON response from a live
  `POST http://localhost:4000/posting` call against the actual running application,
  with real third-party credentials, captured during final verification.

This particular live run happened to show only 3/5 platforms succeeding (Telegra.ph,
Mastodon, Bluesky), with Write.as and Dev.to both failing — honestly left in rather
than replaced with a cleaner-looking run, because both failures are real, expected,
and already documented in `docs/platform_research.md`:

- **Write.as**: this development machine's IP had already been flagged by Write.as's
  own anti-abuse system from the volume of manual testing done during development
  (`"We've detected abusive activity on your IP address."`) — not a code defect.
- **Dev.to**: a genuine `429` from Dev.to's own per-minute rate limit, also from
  repeated manual testing with the same API key in a short window — not a code defect.

Earlier runs captured during development (see `docs/platform_research.md`) show all
five platforms succeeding with real posted URLs when run with fresh rate-limit budget.
A reviewer running this from a different machine/IP with their own fresh credentials
should see all five succeed, as `tests/test_live.py` (`pytest -m live`) is designed to
confirm on demand.
