# What you actually need to provide

Write.as already works with zero setup (confirmed live). Telegra.ph also needs zero
setup — it creates a fresh author account automatically on every publish — but
couldn't be live-tested in this development environment (see `docs/platform_research.md`),
so it's worth confirming yourself even though there's nothing to configure. For the
other three platforms, here's exactly what to get, how to get it, and where it goes in `.env`.

---

## 0. Telegra.ph (zero setup, but unverified — worth a quick check)

**What you need:** nothing. Leave `TELEGRAPH_ACCESS_TOKEN` blank in `.env` and it will
create a fresh account automatically on every publish call.

**To confirm it actually works:** just send a real request (see "After filling in
`.env`" below) and check the `"Telegra.ph"` entry in the response — it should show
`"status": "success"` with a real `https://telegra.ph/...` URL. Open that URL to confirm
the post is actually there.

---

## 1. Mastodon (~3 minutes)

**What you need:** an access token from any Mastodon instance.

**How to get it:**
1. Sign up (free) at [mastodon.social](https://mastodon.social) or any other instance.
2. Go to **Settings → Development → New Application**.
3. Give it a name, leave default scopes (make sure `write:statuses` is checked), click **Submit**.
4. Click into the application you just created — copy the **"Your access token"** value.

**Put in `.env`:**
```
MASTODON_INSTANCE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=<the access token you copied>
```

---

## 2. Dev.to (~2 minutes)

**What you need:** an API key.

**How to get it:**
1. Sign up (free) at [dev.to](https://dev.to).
2. Go to **Settings → Extensions** (`https://dev.to/settings/extensions`).
3. Under "DEV API Keys", generate a new key, give it any description, copy it.

**Put in `.env`:**
```
DEVTO_API_KEY=<the key you copied>
```

---

## 3. Bluesky (~3 minutes)

**What you need:** your handle + an **app password** (not your real login password).

**How to get it:**
1. Sign up (free) at [bsky.app](https://bsky.app) if you don't have an account.
2. Go to **Settings → App passwords** (`https://bsky.app/settings/app-passwords`).
3. Click **Add app password**, name it anything, copy the generated password (looks like `xxxx-xxxx-xxxx-xxxx`).

**Put in `.env`:**
```
BLUESKY_HANDLE=yourhandle.bsky.social
BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx
```

---

## After filling in `.env`

1. Restart the server:
   ```bash
   cd nexora
   source .venv/Scripts/activate   # or .venv\Scripts\activate.bat on Windows cmd
   python -m uvicorn app.main:app --host 0.0.0.0 --port 4000
   ```
2. Test via Swagger (`http://localhost:4000/docs`) or curl:
   ```bash
   curl -X POST http://localhost:4000/posting \
     -H "Content-Type: application/json" \
     -d '{"message": "Testing NEXORA https://example.com"}'
   ```
3. Check each configured platform's result shows `"status": "success"` with a real `posted_url` — open that URL yourself to confirm it's actually live.
4. Once verified, update `docs/platform_research.md`'s "Honesty note on live verification" section to say which platform(s) you personally confirmed, with the real posted URL as evidence — this is the single change that most strengthens the submission.

You don't need all three — even one more live-verified platform beyond Write.as
(and confirming Telegra.ph works) meaningfully improves the submission. Dev.to is the
fastest if you only have time for one of the credentialed three.
