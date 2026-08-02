"""Unit tests — no network access required."""
import os
import random
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.bluesky import build_facets                     # noqa: E402
from bot.render import (BLUESKY_LIMIT, MASTODON_LIMIT,    # noqa: E402
                        build_bluesky_text, build_card, build_mastodon_text)
from bot.selection import State, choose, record          # noqa: E402
from bot.zotero import Article                            # noqa: E402

TAGS = ("#EmpiricalLiteraryStudies", "#SSOL", "#IGEL")


def make(key="AAA", title="A short title", n_authors=1, **kw):
    creators = tuple(f"Author{i}" for i in range(n_authors))
    return Article(
        key=key, title=title, creators=creators,
        year=kw.get("year", "2019"), volume=kw.get("volume", "9"),
        issue=kw.get("issue", "1"), pages=kw.get("pages", "1–20"),
        doi=kw.get("doi", "10.1075/ssol.19001.xyz"),
    )


class TestRender(unittest.TestCase):
    def test_respects_bluesky_limit_even_with_absurd_title(self):
        art = make(title="Lorem ipsum dolor sit amet " * 40)
        text = build_bluesky_text(art, TAGS)
        self.assertLessEqual(len(text), BLUESKY_LIMIT)
        self.assertIn("#SSOL", text)

    def test_respects_mastodon_limit_and_contains_link(self):
        art = make(title="Consectetur adipiscing elit " * 40)
        link = "https://igelsociety.org/ssol-archive/"
        text = build_mastodon_text(art, TAGS, link)
        self.assertLessEqual(len(text), MASTODON_LIMIT)
        self.assertIn(link, text)

    def test_author_formatting(self):
        self.assertEqual(make(n_authors=1).author_string(), "Author0")
        self.assertEqual(make(n_authors=2).author_string(), "Author0 & Author1")
        self.assertEqual(make(n_authors=3).author_string(), "Author0 et al.")

    def test_citation(self):
        self.assertEqual(make().citation(), "SSOL 9(1), 1–20 (2019)")

    def test_card_uses_article_title_and_cta(self):
        card = build_card(make(title="Reading minds"), "View publication")
        self.assertIn("Reading minds", card["title"])
        self.assertIn("View publication", card["description"])

    def test_handles_missing_metadata(self):
        bare = Article(key="B", title="Bare", creators=(), year="", volume="",
                       issue="", pages="", doi="")
        text = build_bluesky_text(bare, TAGS)
        self.assertIn("Bare", text)
        self.assertLessEqual(len(text), BLUESKY_LIMIT)


class TestFacets(unittest.TestCase):
    def test_byte_offsets_are_correct_with_unicode(self):
        text = "Café — “quoted” #SSOL and #IGEL"
        facets = build_facets(text)
        raw = text.encode("utf-8")
        tags = [raw[f["index"]["byteStart"]:f["index"]["byteEnd"]].decode() for f in facets]
        self.assertEqual(tags, ["#SSOL", "#IGEL"])

    def test_ignores_bare_hash_and_numeric_tags(self):
        text = "a # b #1 #ok"
        raw = text.encode("utf-8")
        tags = [raw[f["index"]["byteStart"]:f["index"]["byteEnd"]].decode()
                for f in build_facets(text)]
        self.assertEqual(tags, ["#ok"])


class TestSelection(unittest.TestCase):
    def setUp(self):
        self.articles = [make(key=f"K{i}") for i in range(5)]

    def test_no_repeats_until_exhausted_then_new_cycle(self):
        state = State()
        rng = random.Random(1)
        seen = []
        for _ in range(5):
            art, restarted = choose(self.articles, state, rng)
            self.assertFalse(restarted)
            record(state, art, {"bluesky": "uri"})
            seen.append(art.key)
        self.assertEqual(sorted(seen), sorted(a.key for a in self.articles))
        art, restarted = choose(self.articles, state, rng)
        self.assertTrue(restarted)
        self.assertEqual(state.cycle, 2)

    def test_state_roundtrip(self):
        state = State()
        record(state, self.articles[0], {"mastodon": "url"})
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "sub", "posted.json")
            state.save(path)
            again = State.load(path)
        self.assertEqual(again.posted, [self.articles[0].key])
        self.assertEqual(len(again.history), 1)

    def test_prunes_keys_no_longer_in_library(self):
        state = State(posted=["GONE", "K1"])
        choose(self.articles, state, random.Random(0))
        self.assertNotIn("GONE", state.posted)

    def test_corrupt_state_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "posted.json")
            open(path, "w").write("{not json")
            self.assertEqual(State.load(path).posted, [])


if __name__ == "__main__":
    unittest.main()
