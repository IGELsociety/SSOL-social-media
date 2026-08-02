"""Post a status to Mastodon.

Mastodon builds its own preview card by fetching the OpenGraph tags of the
first link in the status, so the landing-page URL must appear in the text.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "IGEL-SSOL-bot/1.0 (+https://igelsociety.org)"


class MastodonError(RuntimeError):
    pass


class MastodonClient:
    def __init__(self, api_base: str, token: str, visibility: str = "public"):
        self.api_base = api_base.rstrip("/")
        self._token = token
        self.visibility = visibility

    def verify(self) -> dict:
        req = urllib.request.Request(
            f"{self.api_base}/api/v1/accounts/verify_credentials",
            headers={"Authorization": f"Bearer {self._token}", "User-Agent": USER_AGENT},
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            raise MastodonError(f"verify failed HTTP {exc.code}: {exc.read()[:200]!r}") from exc

    def post(self, text: str, idempotency_key: str = "") -> str:
        payload = urllib.parse.urlencode(
            {"status": text, "visibility": self.visibility, "language": "en"}
        ).encode()
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": USER_AGENT,
        }
        if idempotency_key:
            # Prevents a duplicate toot if the workflow is retried.
            headers["Idempotency-Key"] = idempotency_key
        req = urllib.request.Request(
            f"{self.api_base}/api/v1/statuses", data=payload, headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read()).get("url", "")
        except urllib.error.HTTPError as exc:
            raise MastodonError(f"post failed HTTP {exc.code}: {exc.read()[:300]!r}") from exc
