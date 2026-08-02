"""Pick the next article: random order, no repeats until the archive is exhausted.

State lives in a small JSON file that the GitHub Actions workflow commits back
to the repository after each run, so the cycle survives between runs.
"""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from typing import Sequence

from .zotero import Article


@dataclass
class State:
    posted: list[str] = field(default_factory=list)   # item keys already posted this cycle
    cycle: int = 1
    history: list[dict] = field(default_factory=list)  # audit trail of past posts

    @classmethod
    def load(cls, path: str) -> "State":
        if not os.path.exists(path):
            return cls()
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (json.JSONDecodeError, OSError):
            return cls()
        return cls(
            posted=list(raw.get("posted", [])),
            cycle=int(raw.get("cycle", 1)),
            history=list(raw.get("history", [])),
        )

    def save(self, path: str) -> None:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        payload = {"cycle": self.cycle, "posted": self.posted, "history": self.history[-500:]}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.write("\n")


def choose(articles: Sequence[Article], state: State, rng: random.Random | None = None
           ) -> tuple[Article | None, bool]:
    """Return (article, cycle_restarted).

    Picks uniformly at random among articles not yet posted in this cycle. When
    every article has been posted the cycle counter advances and a fresh cycle
    begins, so nothing repeats until everything has had a turn.
    """
    if not articles:
        return None, False
    rng = rng or random.Random()

    known = {a.key for a in articles}
    # drop keys for items that have since left the library
    state.posted = [k for k in state.posted if k in known]

    remaining = [a for a in articles if a.key not in set(state.posted)]
    restarted = False
    if not remaining:
        state.cycle += 1
        state.posted = []
        remaining = list(articles)
        restarted = True

    return rng.choice(remaining), restarted


def record(state: State, article: Article, targets: dict[str, str]) -> None:
    """Mark an article as posted and append an audit entry."""
    if article.key not in state.posted:
        state.posted.append(article.key)
    state.history.append(
        {
            "cycle": state.cycle,
            "key": article.key,
            "title": article.title,
            "doi": article.doi,
            "targets": targets,
        }
    )
