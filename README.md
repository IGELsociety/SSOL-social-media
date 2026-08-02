# SSOL social media bot

Promotes one randomly chosen article from the
[SSOL archive 2011–2022](https://www.zotero.org/groups/6608170/ssol-archive-2011-2022/library)
Zotero group library on **Bluesky** and **Mastodon**, every 3 days, on behalf of
the [IGEL society](https://igelsociety.org).

Each post carries a preview card — *"View publication"* — pointing at the
landing page on igelsociety.org that explains how to access the full text.

## How it works

1. `bot/zotero.py` reads the public Zotero group (no API key needed — the group
   is world-readable).
2. `bot/selection.py` picks an article **at random without replacement**: nothing
   repeats until all 167 have been posted, then a new cycle starts. Progress is
   kept in `state/posted.json`, which the workflow commits back to the repo.
3. `bot/render.py` builds the post text (respecting Bluesky's 300-character and
   Mastodon's 500-character limits).
4. `bot/bluesky.py` / `bot/mastodon.py` publish it.

### A note on the preview cards

The two platforms build cards differently, and it matters here:

| | how the card is built | result |
|---|---|---|
| **Bluesky** | the bot supplies title/description/thumbnail in the post record | card shows **the article's own title** |
| **Mastodon** | the instance scrapes OpenGraph tags from the linked page | card shows **the landing page's** title, identical on every post |

Since all posts link to one shared landing page, Mastodon cards will look the
same each time. The article details are always in the post text itself. Giving
Mastodon per-article cards would require one landing page per article.

## Two ways to reach Mastodon

**Option A — Bluesky only, bridged to the fediverse (simplest).** Post from
Bluesky alone and let [Bridgy Fed](https://fed.brid.gy/docs) mirror the account
into the fediverse. Enable it by logging in at
[fed.brid.gy](https://fed.brid.gy/login) and clicking *Enable*, or by following
[`@ap.brid.gy`](https://bsky.app/profile/ap.brid.gy) from the Bluesky account.
Within minutes the account appears in the fediverse as
`@igelsociety.bsky.social@bsky.brid.gy`, and follows, replies, likes and boosts
flow in both directions.

No code change is required: leave `MASTODON_API_BASE` and `MASTODON_TOKEN`
unset and the bot posts to Bluesky only.

Why it is attractive here:

- The bridge carries the Bluesky post's own card, so fediverse users see the
  **article-specific title** rather than the identical landing-page card that a
  native Mastodon account would scrape.
- One account, one credential, and conversations stay in one place instead of
  fragmenting across two accounts.

What you give up:

- The handle is `@igelsociety.bsky.social@bsky.brid.gy` — not IGEL-branded.
  Custom fediverse handles exist, but that path is for bridged *web sites*, not
  bridged Bluesky accounts.
- **Some instances defederate Bridgy Fed.** Members on those servers will not
  see the account at all. The Bridgy Fed docs have a dedicated FAQ entry about
  this.
- Everything is capped at **Bluesky's 300 characters**, so you lose Mastodon's
  500. Posts already run close to 300, so long titles stay truncated.
- Your fediverse presence depends on a third-party service.

**Option B — a native Mastodon account.** Better branding, never blocked, and
the full 500 characters. Set the two Mastodon secrets and the bot posts to both
platforms.

You can start with Option A and move to Option B later by adding the secrets —
no code change. **If you do, disable the bridge first**, otherwise fediverse
followers receive every post twice (once natively, once bridged).

## Setup

### 1. Publish the landing page

Copy `landing-page/ssol-archive.md` into the igelsociety.org Hugo repository
(e.g. `content/ssol-archive.md`) so it is live at
`https://igelsociety.org/ssol-archive/`. If you publish it at a different path,
set the `LANDING_URL` repository variable to match.

### 2. Create the accounts

- **Bluesky** (required): create the IGEL account, then
  *Settings → Privacy and security → App passwords* and generate one. Use the
  app password, never the account password.
- **Mastodon** (only for Option B): create the account on your chosen instance,
  then *Preferences → Development → New application* with the `write:statuses`
  scope. Copy the access token.
  For Option A, skip this and enable the bridge instead — see
  [Two ways to reach Mastodon](#two-ways-to-reach-mastodon).

### 3. Add repository secrets

*Settings → Secrets and variables → Actions → Secrets*:

| Secret | Example |
|---|---|
| `BLUESKY_HANDLE` (required) | `igelsociety.bsky.social` |
| `BLUESKY_APP_PASSWORD` (required) | `xxxx-xxxx-xxxx-xxxx` |
| `MASTODON_API_BASE` (Option B only) | `https://mastodon.social` |
| `MASTODON_TOKEN` (Option B only) | the access token |

Optional *Variables* (not secrets): `LANDING_URL`, `ZOTERO_GROUP_ID`.

The bot posts to whichever platform is configured — if you only add the Bluesky
secrets, it posts only to Bluesky.

### 4. Try it

From the Actions tab, run **Promote an SSOL article** manually with
*dry run* ticked. It will print exactly what it would publish without posting.

## Running locally

```bash
pip install -r requirements.txt        # only python-dotenv, for .env support
cp .env.example .env                   # then fill it in
python -m bot.main --dry-run           # preview
python -m bot.main --key T3CLWJJG      # force one specific item
python -m bot.main                     # post for real
```

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

## Schedule

`.github/workflows/post.yml` runs at 09:00 UTC on the 1st, 4th, 7th … 28th of
each month — every 3 days, with the 29th–31st skipped so the cadence resets
cleanly each month. Adjust the `cron:` line to change it.

## Safety properties

- **No duplicate posts**: an article is only recorded as posted after at least
  one platform accepts it; if everything fails the run exits non-zero and the
  article is retried next time.
- **Idempotency key** on Mastodon prevents a double toot if a run is retried.
- **No secrets in the repo**: everything comes from environment variables.
- The Zotero library is only ever **read**.
