"""Turning an object into the HTML that gets rendered into an image.

The card is an ordinary Django template in your project, so you design it with
the template language and CSS you already use. It is rendered to a string here
and posted to the API, which renders that string in real Chrome.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

from django.template.loader import render_to_string
from django.utils import timezone

from html2img_django import conf
from html2img_django.conf import ResolvedSettings
from html2img_django.registry import og_images

__all__ = ["build_context", "fingerprint", "render_card", "render_sample", "settings_for"]


def settings_for(obj: Any) -> ResolvedSettings:
    """Resolve the render settings for an object's model."""
    return conf.resolve(og_images.options_for(type(obj)))


def build_context(obj: Any) -> Dict[str, Any]:
    """The context a card template is rendered with.

    Always includes ``object``, the model name (so a ``Post`` is also available
    as ``post``), ``og_headline``, ``og_subtitle``, ``site_name`` and
    ``site_logo``. The object's own :meth:`og_image_context` and any ``context``
    callable given at registration are merged over the top, in that order.
    """
    context: Dict[str, Any] = {
        "object": obj,
        "og_headline": obj.og_image_headline_text(),
        "og_subtitle": obj.og_image_subtitle_text(),
        "site_name": conf.site_name(),
        "site_logo": conf.get_setting("SITE_LOGO") or "",
    }

    meta = getattr(obj, "_meta", None)

    if meta is not None:
        context[meta.model_name] = obj

    context.update(obj.og_image_context() or {})

    extra = og_images.context_for(type(obj))

    if extra is not None:
        context.update(extra(obj) or {})

    return context


def render_card(obj: Any, resolved: Optional[ResolvedSettings] = None) -> str:
    """Render an object's card template to an HTML string. No API call."""
    resolved = resolved or settings_for(obj)

    return render_to_string(resolved.template, build_context(obj)).strip()


def render_sample(resolved: Optional[ResolvedSettings] = None) -> str:
    """Render the default template with representative sample data.

    Used by the preview view when there is no object to render against, so a
    designer can work on the card before any content exists.
    """
    resolved = resolved or conf.resolve()

    return render_to_string(resolved.template, sample_context()).strip()


def sample_context() -> Dict[str, Any]:
    """Representative data for a preview with no object behind it."""
    return {
        "object": None,
        "og_headline": "How real Chrome rendering changes social images",
        "og_subtitle": "A worked example of the Open Graph pipeline",
        "site_name": conf.site_name() or "example.com",
        "site_logo": conf.get_setting("SITE_LOGO") or "",
        "author": "Jamie Rivera",
        "date": timezone.now(),
    }


def fingerprint(html: str, resolved: ResolvedSettings) -> str:
    """A fingerprint of everything that affects the rendered image.

    Saving an object without changing its card leaves this unchanged, which is
    what lets the pipeline skip the render and spend no credit.
    """
    parts = "|".join(
        [
            resolved.template,
            f"{resolved.width}x{resolved.height}@{resolved.dpi}",
            resolved.format,
            html,
        ]
    )

    return hashlib.sha1(parts.encode("utf-8"), usedforsecurity=False).hexdigest()
