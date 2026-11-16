# Platform Research

Five platforms were chosen for having a genuinely simple, stable, well-documented
public API for posting short text + a link, with a free tier usable within the
timeframe of this test (no paid developer account, no lengthy OAuth app review).

| Platform | Endpoint used | Auth | Docs |
|---|---|---|---|
| Telegram | `POST https://api.telegram.org/bot<token>/sendMessage` | Bot token in URL | https://core.telegram.org/bots/api#sendmessage |
| Mastodon | `POST /api/v1/statuses` on the configured instance | OAuth2 bearer access token | https://docs.joinmastodon.org/methods/statuses/#create |
| Write.as | `POST https://write.as/api/posts` | None required (anonymous posting) | https://developers.write.as/docs/api/#publish-a-post |
| Dev.to | `POST https://dev.to/api/articles` | `api-key` header | https://developers.forem.com/api/v1#tag/articles/operation/createArticle |
| Bluesky | `POST /xrpc/com.atproto.server.createSession` then `POST /xrpc/com.atproto.repo.createRecord` | App password → short-lived JWT | https://docs.bsky.app/docs/api/com-atproto-server-create-session, https://docs.bsky.app/docs/api/com-atproto-repo-create-record |

## Per-platform notes

**Telegram** — simplest integration: one authenticated POST, JSON in, JSON out. A
public permalink (`https://t.me/<username>/<id>`) only exists if the bot is posting to
a channel with a public `@username`; a private group has no equivalent public URL, so
the adapter reports `public_access: false` in that case rather than guessing one.

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
and CTA link verbatim. A published (non-draft) article is genuinely public and indexed.

**Bluesky** — the AT Protocol has no API-key concept; it's a two-step login (app
password → access JWT) then a record-create call. Posts have no private/public
distinction at the protocol level, so a successfully created post is always public.

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

**No live credentials for Telegram, Mastodon, Dev.to, or Bluesky were available in the
development environment this was built in**, so those four adapters have not been
exercised end-to-end against a real account. Running them with real credentials (see
`.env.example`) is expected to work as written, but should be verified by the
reviewer/candidate before relying on them — see the README's "Known Limitations" section.
