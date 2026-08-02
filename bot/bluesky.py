"""Minimal AT Protocol client — just enough to post with an external card.

Implemented against the XRPC HTTP API with the standard library so the bot has
no heavyweight dependencies to keep patched.
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone

USER_AGENT = "IGEL-SSOL-bot/1.0 (+https://igelsociety.org)"
MAX_THUMB_BYTES = 976_560  # Bluesky rejects blobs larger than ~1 MB
TAG_RE = re.compile(r"(?<![\w#])#([A-Za-z][A-Za-z0-9_]*)")


class BlueskyError(RuntimeError):
    pass


def _post(url: str, payload: bytes, headers: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        raise BlueskyError(f"{url} -> HTTP {exc.code}: {exc.read()[:300]!r}") from exc


def _get_bytes(url: str, timeout: int = 60) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), resp.headers.get("Content-Type", "application/octet-stream")


def build_facets(text: str) -> list[dict]:
    """Byte-offset facets so hashtags render as links (AT Proto uses UTF-8 offsets)."""
    facets = []
    raw = text.encode("utf-8")
    for match in TAG_RE.finditer(text):
        start = len(text[: match.start()].encode("utf-8"))
        end = len(text[: match.end()].encode("utf-8"))
        facets.append(
            {
                "index": {"byteStart": start, "byteEnd": end},
                "features": [{"$type": "app.bsky.richtext.facet#tag", "tag": match.group(1)}],
            }
        )
    assert all(f["index"]["byteEnd"] <= len(raw) for f in facets)
    return facets


class BlueskyClient:
    def __init__(self, handle: str, app_password: str, pds: str = "https://bsky.social"):
        self.pds = pds.rstrip("/")
        self.handle = handle
        self._password = app_password
        self.did: str | None = None
        self._jwt: str | None = None

    # --- auth -----------------------------------------------------------
    def login(self) -> None:
        data = _post(
            f"{self.pds}/xrpc/com.atproto.server.createSession",
            json.dumps({"identifier": self.handle, "password": self._password}).encode(),
            {"Content-Type": "application/json", "User-Agent": USER_AGENT},
        )
        self._jwt = data.get("accessJwt")
        self.did = data.get("did")
        if not self._jwt or not self.did:
            raise BlueskyError("login did not return a session")

    def _auth_headers(self, content_type: str = "application/json") -> dict:
        if not self._jwt:
            raise BlueskyError("not logged in")
        return {
            "Authorization": f"Bearer {self._jwt}",
            "Content-Type": content_type,
            "User-Agent": USER_AGENT,
        }

    # --- media ----------------------------------------------------------
    def upload_thumb(self, image_url: str) -> dict | None:
        """Fetch an image and upload it as a blob; returns None if unusable."""
        try:
            blob, content_type = _get_bytes(image_url)
        except Exception:
            return None
        if not blob or len(blob) > MAX_THUMB_BYTES:
            return None
        if not content_type.startswith("image/"):
            content_type = "image/png"
        try:
            res = _post(
                f"{self.pds}/xrpc/com.atproto.repo.uploadBlob",
                blob,
                self._auth_headers(content_type),
            )
        except BlueskyError:
            return None
        return res.get("blob")

    # --- posting --------------------------------------------------------
    def post(self, text: str, link: str, card_title: str, card_description: str,
             thumb_url: str = "") -> str:
        external = {"uri": link, "title": card_title, "description": card_description}
        if thumb_url:
            thumb = self.upload_thumb(thumb_url)
            if thumb:
                external["thumb"] = thumb

        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "langs": ["en"],
            "facets": build_facets(text),
            "embed": {"$type": "app.bsky.embed.external", "external": external},
        }
        res = _post(
            f"{self.pds}/xrpc/com.atproto.repo.createRecord",
            json.dumps(
                {"repo": self.did, "collection": "app.bsky.feed.post", "record": record}
            ).encode(),
            self._auth_headers(),
        )
        return res.get("uri", "")
