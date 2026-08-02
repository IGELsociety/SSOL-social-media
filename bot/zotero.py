"""Read the SSOL archive from the public Zotero group library.

The group (SSOL-archive-2011-2022) is world-readable, so no API key is needed
for the bot. Only top-level bibliographic items are returned; attachments and
notes are filtered out.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterable

USER_AGENT = "IGEL-SSOL-bot/1.0 (+https://igelsociety.org)"
PAGE_SIZE = 100


@dataclass(frozen=True)
class Article:
    key: str
    title: str
    creators: tuple[str, ...]
    year: str
    volume: str
    issue: str
    pages: str
    doi: str

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""

    def author_string(self, max_names: int = 2) -> str:
        """'Smith', 'Smith & Jones', or 'Smith et al.'"""
        names = [n for n in self.creators if n]
        if not names:
            return ""
        if len(names) == 1:
            return names[0]
        if len(names) == 2 and max_names >= 2:
            return f"{names[0]} & {names[1]}"
        return f"{names[0]} et al."

    def citation(self) -> str:
        """Compact source line, e.g. 'SSOL 11(2), 266–282 (2022)'."""
        bits = []
        if self.volume:
            vol = f"SSOL {self.volume}"
            if self.issue:
                vol += f"({self.issue})"
            bits.append(vol)
        if self.pages:
            bits.append(self.pages)
        line = ", ".join(bits)
        if self.year:
            line = f"{line} ({self.year})" if line else f"({self.year})"
        return line


def _fetch_json(url: str, timeout: int = 60):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Zotero-API-Version": "3"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _year_from_date(date_str: str) -> str:
    for chunk in str(date_str).replace("/", "-").split("-"):
        chunk = chunk.strip()
        if len(chunk) == 4 and chunk.isdigit():
            return chunk
    digits = "".join(c for c in str(date_str) if c.isdigit())
    return digits[:4] if len(digits) >= 4 else str(date_str).strip()


def _creator_names(creators: Iterable[dict]) -> tuple[str, ...]:
    names = []
    for c in creators or []:
        if c.get("creatorType") != "author":
            continue
        last = (c.get("lastName") or "").strip()
        if last:
            names.append(last)
        elif c.get("name"):
            names.append(str(c["name"]).strip())
    return tuple(names)


def fetch_articles(group_id: str, api_base: str = "https://api.zotero.org") -> list[Article]:
    """Return every top-level bibliographic item in the group."""
    articles: list[Article] = []
    start = 0
    while True:
        url = f"{api_base}/groups/{group_id}/items/top?format=json&limit={PAGE_SIZE}&start={start}"
        batch = _fetch_json(url)
        if not batch:
            break
        for entry in batch:
            data = entry.get("data", {})
            if data.get("itemType") in {"attachment", "note"}:
                continue
            title = (data.get("title") or "").strip()
            if not title:
                continue
            articles.append(
                Article(
                    key=data.get("key", ""),
                    title=title,
                    creators=_creator_names(data.get("creators")),
                    year=_year_from_date(data.get("date", "")),
                    volume=str(data.get("volume", "")).strip(),
                    issue=str(data.get("issue", "")).strip(),
                    pages=str(data.get("pages", "")).strip(),
                    doi=str(data.get("DOI", "")).strip(),
                )
            )
        if len(batch) < PAGE_SIZE:
            break
        start += PAGE_SIZE
    return articles
