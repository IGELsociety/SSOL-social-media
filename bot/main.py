"""Entry point: pick one SSOL article and promote it on Bluesky and Mastodon.

  python -m bot.main --dry-run     # show what would be posted, touch nothing
  python -m bot.main               # post for real
  python -m bot.main --key ABCD123 # force a specific Zotero item
"""
from __future__ import annotations

import argparse
import random
import sys

from .bluesky import BlueskyClient, BlueskyError
from .config import load_config
from .mastodon import MastodonClient, MastodonError
from .render import build_bluesky_text, build_card, build_mastodon_text
from .selection import State, choose, record
from .zotero import fetch_articles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote one SSOL archive article.")
    parser.add_argument("--dry-run", action="store_true", help="print, do not post")
    parser.add_argument("--key", help="force a specific Zotero item key")
    parser.add_argument("--seed", type=int, help="seed the RNG (testing)")
    args = parser.parse_args(argv)

    cfg = load_config()
    dry = args.dry_run or cfg.dry_run

    articles = fetch_articles(cfg.zotero_group_id, cfg.zotero_api_base)
    if not articles:
        print("No articles returned by Zotero — aborting.", file=sys.stderr)
        return 1
    print(f"Fetched {len(articles)} items from Zotero group {cfg.zotero_group_id}")

    state = State.load(cfg.state_path)

    if args.key:
        article = next((a for a in articles if a.key == args.key), None)
        if article is None:
            print(f"No item with key {args.key}", file=sys.stderr)
            return 1
        restarted = False
    else:
        rng = random.Random(args.seed) if args.seed is not None else random.Random()
        article, restarted = choose(articles, state, rng)
    if article is None:
        print("Nothing to post.", file=sys.stderr)
        return 1
    if restarted:
        print(f"All articles posted — starting cycle {state.cycle}.")

    remaining = len(articles) - len(state.posted)
    print(f"Selected: {article.title[:80]!r} ({remaining} left in cycle {state.cycle})")

    bsky_text = build_bluesky_text(article, cfg.hashtags)
    mast_text = build_mastodon_text(article, cfg.hashtags, cfg.landing_url)
    card = build_card(article, cfg.card_cta, cfg.card_title_prefix)

    print("\n--- Bluesky ---")
    print(bsky_text)
    print(f"[card] {card['title'][:70]!r} | {card['description'][:70]!r} -> {cfg.landing_url}")
    print("\n--- Mastodon ---")
    print(mast_text)

    if dry:
        print("\nDRY RUN — nothing posted, state unchanged.")
        return 0

    targets: dict[str, str] = {}
    failures: list[str] = []

    if cfg.bluesky_enabled:
        try:
            client = BlueskyClient(cfg.bluesky_handle, cfg.bluesky_app_password, cfg.bluesky_pds)
            client.login()
            uri = client.post(
                bsky_text, cfg.landing_url, card["title"], card["description"], cfg.card_thumb_url
            )
            targets["bluesky"] = uri
            print(f"Bluesky OK: {uri}")
        except BlueskyError as exc:
            failures.append(f"bluesky: {exc}")
            print(f"Bluesky FAILED: {exc}", file=sys.stderr)
    else:
        print("Bluesky credentials absent — skipped.")

    if cfg.mastodon_enabled:
        try:
            client = MastodonClient(cfg.mastodon_api_base, cfg.mastodon_token, cfg.mastodon_visibility)
            url = client.post(mast_text, idempotency_key=f"ssol-{state.cycle}-{article.key}")
            targets["mastodon"] = url
            print(f"Mastodon OK: {url}")
        except MastodonError as exc:
            failures.append(f"mastodon: {exc}")
            print(f"Mastodon FAILED: {exc}", file=sys.stderr)
    else:
        print("Mastodon credentials absent — skipped.")

    if not targets:
        # Nothing went out: leave the article unposted so it is retried next run.
        print("No post succeeded; state left unchanged.", file=sys.stderr)
        return 1

    record(state, article, targets)
    state.save(cfg.state_path)
    print(f"State saved -> {cfg.state_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
