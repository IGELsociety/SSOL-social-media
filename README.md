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

## Setup

### 1. Add repository secrets

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

### 2. Try it

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
