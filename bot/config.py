"""Configuration for the SSOL archive promotion bot.

Everything is read from environment variables so the same code runs locally
(via a .env file) and in GitHub Actions (via repository secrets).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_bool(name: str, default: bool = False) -> bool:
    raw = _env(name, str(default)).lower()
    return raw in {"1", "true", "yes", "on"}


@dataclass
class Config:
    # --- Zotero (public group: no API key required for reading) ---
    zotero_group_id: str = field(default_factory=lambda: _env("ZOTERO_GROUP_ID", "6608170"))
    zotero_api_base: str = "https://api.zotero.org"

    # --- Landing page the preview card points at ---
    landing_url: str = field(
        default_factory=lambda: _env("LANDING_URL", "https://igelsociety.org/ssol-archive/")
    )
    card_title_prefix: str = field(default_factory=lambda: _env("CARD_TITLE_PREFIX", ""))
    card_cta: str = field(default_factory=lambda: _env("CARD_CTA", "View publication"))
    card_thumb_url: str = field(
        default_factory=lambda: _env("CARD_THUMB_URL", "https://igelsociety.org/images/logo.png")
    )

    # --- Bluesky ---
    bluesky_handle: str = field(default_factory=lambda: _env("BLUESKY_HANDLE"))
    bluesky_app_password: str = field(default_factory=lambda: _env("BLUESKY_APP_PASSWORD"))
    bluesky_pds: str = field(default_factory=lambda: _env("BLUESKY_PDS", "https://bsky.social"))

    # --- Mastodon ---
    mastodon_api_base: str = field(default_factory=lambda: _env("MASTODON_API_BASE"))
    mastodon_token: str = field(default_factory=lambda: _env("MASTODON_TOKEN"))
    mastodon_visibility: str = field(default_factory=lambda: _env("MASTODON_VISIBILITY", "public"))

    # --- Behaviour ---
    state_path: str = field(default_factory=lambda: _env("STATE_PATH", "state/posted.json"))
    hashtags: tuple[str, ...] = ("#EmpiricalLiteraryStudies", "#SSOL", "#IGEL")
    dry_run: bool = field(default_factory=lambda: _env_bool("DRY_RUN", False))

    @property
    def bluesky_enabled(self) -> bool:
        return bool(self.bluesky_handle and self.bluesky_app_password)

    @property
    def mastodon_enabled(self) -> bool:
        return bool(self.mastodon_api_base and self.mastodon_token)


def load_config() -> Config:
    """Load config, reading a local .env file first if python-dotenv is present."""
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass
    return Config()
