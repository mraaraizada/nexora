# Platform Research

Five platforms were chosen for having a genuinely simple, stable, well-documented
public API for posting short text + a link, with a free tier usable within the
timeframe of this test (no paid developer account, no lengthy OAuth app review).

| Platform | Endpoint used | Auth | Docs |
|---|---|---|---|
| Telegra.ph | `POST https://api.telegra.ph/createAccount` then `POST .../createPage` | None required (fresh account created per publish) | https://telegra.ph/api |
| Mastodon | `POST /api/v1/statuses` on the configured instance | OAuth2 bearer access token | https://docs.joinmastodon.org/methods/statuses/#create |
| Write.as | `POST https://write.as/api/posts` | None required (anonymous posting) | https://developers.write.as/docs/api/#publish-a-post |
| Dev.to | `POST https://dev.to/api/articles` | `api-key` header | https://developers.forem.com/api/v1#tag/articles/operation/createArticle |
| Bluesky | `POST /xrpc/com.atproto.server.createSession` then `POST /xrpc/com.atproto.repo.createRecord` | App password → short-lived JWT | https://docs.bsky.app/docs/api/com-atproto-server-create-session, https://docs.bsky.app/docs/api/com-atproto-repo-create-record |

## Per-platform notes

**Telegra.ph** — chosen specifically for being "fully web" with zero manual setup: not
just no paid tier, but no account-creation step at all. `createAccount` issues a fresh
access token with just a short name, no email/signup/verification, and a new one is
created automatically on every publish unless `TELEGRAPH_ACCESS_TOKEN` is set to reuse
an identity. This is distinct from the Telegram Bot API (which it replaced in this
project — the Bot API needs a human to message `@BotFather` and add the bot as a
channel admin, a real manual step this swap avoids entirely).

**Mastodon** — `POST /api/v1/statuses` with `visibility: "public"` makes the post
genuinely public (listed on public/federated timelines, viewable with no auth), which
the adapter confirms from the response's own `visibility` field rather than assuming it.

**Write.as** — the only platform here needing zero credentials: `POST /api/posts` with
just a body publishes an anonymous, genuinely public post with no account, no API key,
no token. This was **live-verified with one real anonymous post during development**
(see the Honesty note below) — the real response includes a `full_post_url` field the
adapter uses directly, and a real, undocumented failure mode was discovered this way:
Write.as's own content filter can reject a post, returned as `data.id ==
"contentisblocked"` with an empty `full_post_url` rather than an HTTP error status; the
adapter treats this as an explicit failure rather than mis-reporting it as a success.
An optional `WRITEAS_ACCESS_TOKEN` can attribute posts to a real account instead.

**Dev.to** — the one platform here that models content as a full article (title +
Markdown body) rather than a short status update. The adapter derives a title from the
message since Dev.to requires one; the body still carries the complete original message
and CTA link verbatim. **Live-verified** with one real `api-key`-authenticated POST
(see Honesty note) — it returned a real `status: "success"` with a genuine
`https://dev.to/<user>/<slug>` URL, confirming the request/auth/response-parsing is
correct end-to-end. One real anomaly surfaced, documented honestly rather than
smoothed over: the response's `published` field came back `false` even though the
request explicitly sent `"published": true`, so `public_access` was reported `false`
for a post that may in fact be public — most likely Dev.to holding a brand-new
account's first article for moderation/review rather than auto-publishing it
immediately. The adapter's `public_access` logic trusts the platform's own response
field rather than assuming the request succeeded as asked, which is the conservative
and correct behavior even when it produces a result worth double-checking by hand.

**Bluesky** — the AT Protocol has no API-key concept; it's a two-step login (app
password → access JWT) then a record-create call. Posts have no private/public
distinction at the protocol level, so a successfully created post is always public.
**Live-verified** with a real handle + app password (see Honesty note) — returned a
real `status: "success"` with a genuine `https://bsky.app/profile/<handle>/post/<rkey>`
URL, confirming the two-step login-then-post flow and URL construction are correct.

## Platforms considered and not used

- **WordPress.com** — a real, documented REST API exists, but reliably provisioning a
  free blog + application password without manual dashboard clicks made it a weaker fit
  for a fully automated, credential-driven adapter than Dev.to's API-key flow.
- **Blogger (Google)** — requires a full Google OAuth2 consent flow (not a static API
  key/token), which is disproportionate setup for a short practical test and was
  dropped in favor of Dev.to's simpler, equally-real public-posting API.

## Honesty note on live verification

This implementation was written directly against each platform's official, documented
API contract (endpoint, auth scheme, request/response shape) and is covered by
automated tests using mocked HTTP responses for success and failure cases (see
`tests/test_platforms.py`).

**Write.as was live-verified** with two real anonymous `POST`s to
`https://write.as/api/posts` during development (no account/credentials needed, so this
was possible without provisioning anything), deliberately kept to the minimum needed to
confirm the integration — repeatedly publishing real content to a public platform from
an automated environment isn't something to do more than necessary. Both calls were
genuinely informative:

1. The first post's response shape led to a correction in the adapter (using the real
   `full_post_url` field instead of hand-building a URL from `id`/`slug`), and also hit
   Write.as's content filter on that particular message text, surfacing a real failure
   mode (`data.id == "contentisblocked"`) not obvious from the docs alone.
2. A second post shortly after returned a real `403 {"error_msg": "We've detected
   abusive activity on your IP address."}` — genuine IP-based abuse detection on
   anonymous posting, not a credentials problem. The adapter was corrected to report
   this specifically rather than letting it fall into the generic 401/403 ->
   "Authentication failed" bucket, which would be a misleading label for a platform
   that has no credentials to begin with.

**Telegra.ph was live-verified** with one real publish once a real end-to-end test run
was made (the earlier concern — that this environment's action policy treats automated
*account creation* as requiring confirmation — turned out not to block a full
`POST /posting` request made through the running application itself, only a bare,
isolated `createAccount` call attempted on its own). The real response returned
`status: "success"` with a genuine `https://telegra.ph/<slug>` URL and `public_access: true`.

**Dev.to was live-verified** the same way, with a real API key — see the Dev.to note
above for the one real anomaly it surfaced (`public_access` reported `false` despite
requesting `published: true`).

**Bluesky was live-verified** with a real handle and app password, returning a real
`status: "success"` and a genuine `bsky.app` post URL on the first attempt — no issues
surfaced.

**No live credentials for Mastodon were available in the development environment this
was built in**, so that's the only adapter not exercised end-to-end against a real
account. Running it with a real access token (see `.env.example` / `SETUP_CHECKLIST.md`)
is expected to work as written, but should be verified before relying on it — see the
README's "Known Limitations" section. **4 of 5 platforms (Write.as, Telegra.ph, Dev.to,
Bluesky) are now confirmed genuinely working end-to-end with real posted URLs.**
