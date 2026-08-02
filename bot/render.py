"""Compose the post text and preview-card metadata for one article.

Bluesky counts *graphemes* and caps posts at 300; the link lives in the preview
card, so it costs no characters there. Mastodon allows 500 and must contain the
URL in the text for the instance to scrape a card.
"""
from __future__ import annotations

from .zotero import Article

BLUESKY_LIMIT = 300
MASTODON_LIMIT = 500
INTRO = "From the SSOL archive:"


def _shorten(text: str, limit: int) -> str:
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip(" ,;:.—-") + "…"


def _byline(article: Article) -> str:
    author = article.author_string()
    citation = article.citation()
    if author and citation:
        return f"{author} — {citation}"
    return author or citation


def build_text(article: Article, hashtags: tuple[str, ...], limit: int,
               link: str = "") -> str:
    """Assemble the post, trimming the title first so nothing else is lost."""
    tag_line = " ".join(hashtags)
    byline = _byline(article)

    fixed_parts = [INTRO, byline, tag_line]
    if link:
        fixed_parts.append(link)
    # +1 newline between each block, title occupies whatever is left
    overhead = sum(len(p) for p in fixed_parts if p) + len(
        [p for p in fixed_parts if p]
    )
    budget = limit - overhead
    if budget < 40:                      # pathological: drop hashtags before the title
        tag_line = ""
        fixed_parts = [INTRO, byline] + ([link] if link else [])
        overhead = sum(len(p) for p in fixed_parts if p) + len(
            [p for p in fixed_parts if p]
        )
        budget = limit - overhead

    title = _shorten(f"“{article.title}”", max(budget, 20))

    lines = [INTRO, title]
    if byline:
        lines.append(byline)
    if tag_line:
        lines.append(tag_line)
    if link:
        lines.append(link)
    text = "\n".join(lines)

    if len(text) > limit:                # last-resort hard trim
        text = text[: limit - 1].rstrip() + "…"
    return text


def build_bluesky_text(article: Article, hashtags: tuple[str, ...]) -> str:
    # No URL in the body: the external embed card carries the link.
    return build_text(article, hashtags, BLUESKY_LIMIT)


def build_mastodon_text(article: Article, hashtags: tuple[str, ...], link: str) -> str:
    # The URL must be in the text so Mastodon fetches the OpenGraph card.
    return build_text(article, hashtags, MASTODON_LIMIT, link=link)


def build_card(article: Article, cta: str, title_prefix: str = "") -> dict:
    """Title/description for the Bluesky external embed.

    The card title is the article itself, so each post looks distinct even
    though every card points at the same landing page.
    """
    title = _shorten(f"{title_prefix}{article.title}", 300)
    bits = [b for b in (_byline(article), cta) if b]
    return {"title": title, "description": " · ".join(bits)}
