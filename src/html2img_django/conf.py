"""Settings resolution.

Everything is configured through a single ``HTML2IMG`` dict in your Django
settings. Anything you leave out falls back to the defaults below, and the API
key falls back to the ``HTML2IMG_API_KEY`` environment variable.

Settings are resolved through a cascade, from least to most specific:

1. the defaults in this module,
2. the ``HTML2IMG`` dict in your settings,
3. the options a model was registered with,
4. per-object overrides (a headline, a subtitle, a custom image, an opt-out).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

SETTINGS_NAME = "HTML2IMG"

DEFAULTS: Dict[str, Any] = {
    # Credentials. The environment is the canonical source for the key.
    "API_KEY": None,
    "BASE_URL": None,
    "TIMEOUT": 35.0,
    # The card design and its dimensions.
    "TEMPLATE": "html2img_django/default.html",
    "WIDTH": 1200,
    "HEIGHT": 630,
    "DPI": 2,
    "FORMAT": "png",
    # Where the finished render lives: "cdn" keeps the i.html2img.com URL,
    # "media" downloads it into your Django storage.
    "STORAGE": "cdn",
    "MEDIA_PATH": "og-images/{app_label}/{model_name}/{pk}.{extension}",
    # Details passed to every template, and the fallback used when an object
    # has no image of its own.
    "SITE_NAME": None,
    "SITE_LOGO": None,
    "DEFAULT_IMAGE": None,
    # What happens when a registered object is saved: "thread" renders in a
    # background thread, "sync" renders inline, "off" leaves it to you.
    "ON_SAVE": "thread",
    # A master switch. Set False in tests and local development to stop the
    # package from calling the API at all.
    "ENABLED": True,
}

STORAGE_MODES = ("cdn", "media")
ON_SAVE_MODES = ("thread", "sync", "off")


def get_setting(key: str, default: Any = None) -> Any:
    """A single setting, with the project's ``HTML2IMG`` dict layered over the defaults."""
    configured = getattr(django_settings, SETTINGS_NAME, None) or {}

    if not isinstance(configured, dict):
        raise ImproperlyConfigured(f"settings.{SETTINGS_NAME} must be a dict.")

    unknown = set(configured) - set(DEFAULTS)

    if unknown:
        raise ImproperlyConfigured(
            f"Unknown {SETTINGS_NAME} settings: {', '.join(sorted(unknown))}. "
            f"Valid keys are: {', '.join(sorted(DEFAULTS))}."
        )

    if key in configured and configured[key] is not None:
        return configured[key]

    if default is not None:
        return default

    return DEFAULTS.get(key)


def api_key() -> Optional[str]:
    """The API key: the ``HTML2IMG`` setting if given, otherwise the environment."""
    configured = get_setting("API_KEY")

    if configured:
        return str(configured)

    return os.environ.get("HTML2IMG_API_KEY") or None


def is_enabled() -> bool:
    """Whether rendering is switched on and a key is available."""
    return bool(get_setting("ENABLED")) and bool(api_key())


def site_name() -> str:
    """The site name passed to every template."""
    configured = get_setting("SITE_NAME")

    if configured:
        return str(configured)

    return _site_name_from_sites_framework() or ""


def _site_name_from_sites_framework() -> Optional[str]:
    if "django.contrib.sites" not in (django_settings.INSTALLED_APPS or []):
        return None

    try:
        from django.contrib.sites.models import Site

        return Site.objects.get_current().name
    except Exception:  # pragma: no cover - the sites table may not exist yet
        return None


@dataclass(frozen=True)
class ResolvedSettings:
    """The settings that apply to a single render, after the cascade is resolved."""

    template: str
    width: int
    height: int
    dpi: int
    format: str
    storage: str
    media_path: str

    @property
    def is_media_storage(self) -> bool:
        """Whether the render should be downloaded into Django's storage."""
        return self.storage == "media"

    @property
    def extension(self) -> str:
        """The file extension for this render's format."""
        return "pdf" if self.format == "pdf" else "png"

    @property
    def content_type(self) -> str:
        """The MIME type for this render's format."""
        return "application/pdf" if self.format == "pdf" else "image/png"


def resolve(overrides: Optional[Dict[str, Any]] = None) -> ResolvedSettings:
    """Build the settings for a render, layering registration options on top.

    :param overrides: The options a model was registered with, if any.
    """
    options = {key: value for key, value in (overrides or {}).items() if value is not None}

    storage = str(options.get("storage", get_setting("STORAGE")))

    if storage not in STORAGE_MODES:
        raise ImproperlyConfigured(
            f"HTML2IMG['STORAGE'] must be one of {STORAGE_MODES}, got {storage!r}."
        )

    return ResolvedSettings(
        template=str(options.get("template", get_setting("TEMPLATE"))),
        width=int(options.get("width", get_setting("WIDTH"))),
        height=int(options.get("height", get_setting("HEIGHT"))),
        dpi=int(options.get("dpi", get_setting("DPI"))),
        format=str(options.get("format", get_setting("FORMAT"))),
        storage=storage,
        media_path=str(options.get("media_path", get_setting("MEDIA_PATH"))),
    )


def on_save_mode() -> str:
    """How a save should be handled: ``thread``, ``sync`` or ``off``."""
    mode = str(get_setting("ON_SAVE"))

    if mode not in ON_SAVE_MODES:
        raise ImproperlyConfigured(
            f"HTML2IMG['ON_SAVE'] must be one of {ON_SAVE_MODES}, got {mode!r}."
        )

    return mode
