"""The generation pipeline.

Resolve the settings for an object, render its card template, send the HTML to
the API, and store the returned URL back on the object. A fingerprint of the
render inputs is stored alongside it, so saving an object without changing its
card costs nothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable, List, Optional

from html2img import Html2imgError

from html2img_django import conf, storage
from html2img_django.client import get_client
from html2img_django.models import OpenGraphImageMixin
from html2img_django.rendering import fingerprint, render_card, settings_for

logger = logging.getLogger("html2img_django")

__all__ = ["GenerationResult", "generate", "generate_many", "generate_result"]


@dataclass(frozen=True)
class GenerationResult:
    """What happened to one object.

    Distinguishes an image that was actually rendered (a credit was spent) from
    one that was reused because nothing about the card had changed.
    """

    url: Optional[str] = None
    rendered: bool = False
    reason: Optional[str] = None
    """Why nothing was rendered.

    One of ``"disabled"``, ``"unsaved"``, ``"opted-out"``, ``"unchanged"``,
    ``"error"`` or ``"no-url"``. ``None`` when a render happened.
    """

    @property
    def ok(self) -> bool:
        """Whether the object ended up with an image, rendered or reused."""
        return self.url is not None

    @property
    def reused(self) -> bool:
        """Whether an existing image was kept because the inputs were unchanged."""
        return self.reason == "unchanged"


def generate(obj: OpenGraphImageMixin, force: bool = False) -> Optional[str]:
    """Generate (or reuse) an object's Open Graph image and store it.

    :param obj: A saved instance of a model using
        :class:`~html2img_django.models.OpenGraphImageMixin`.
    :param force: Re-render even when the inputs are unchanged.
    :returns: The stored URL, or ``None`` when nothing was rendered.
    """
    return generate_result(obj, force=force).url


def generate_result(obj: OpenGraphImageMixin, force: bool = False) -> GenerationResult:
    """Like :func:`generate`, but reports what happened.

    Useful in your own tasks and reporting, where "reused an existing image"
    and "rendered a new one" mean different things — only the second spends a
    credit.
    """
    if not conf.is_enabled():
        logger.debug("Skipping %s: rendering is disabled or no API key is set.", obj)

        return GenerationResult(reason="disabled")

    if obj.pk is None:
        logger.debug("Skipping an unsaved %s.", type(obj).__name__)

        return GenerationResult(reason="unsaved")

    if not obj.should_generate_og_image():
        logger.debug("Skipping %s: it opted out or has a custom image.", obj)

        return GenerationResult(reason="opted-out")

    resolved = settings_for(obj)
    html = render_card(obj, resolved)
    digest = fingerprint(html, resolved)

    if not force and obj.og_image_hash == digest and obj.og_image_url:
        logger.debug("Reusing the image for %s: the card is unchanged.", obj)

        return GenerationResult(url=obj.og_image_url, reason="unchanged")

    client = get_client()

    try:
        response = client.html(
            html,
            width=resolved.width,
            height=resolved.height,
            dpi=resolved.dpi,
            format=resolved.format,
        )
    except Html2imgError as error:
        logger.error(
            "Render failed for %s (%s): %s",
            obj,
            getattr(error, "error_code", None) or getattr(error, "status_code", None),
            error,
        )

        return GenerationResult(reason="error")

    url = response.url

    if not url:
        logger.error("The API returned no URL for %s (status %s).", obj, response.status)

        return GenerationResult(reason="no-url")

    if resolved.is_media_storage:
        url = storage.localise(client, url, obj, resolved) or url

    _persist(obj, url, digest)

    return GenerationResult(url=url, rendered=True)


def generate_many(
    objects: Iterable[OpenGraphImageMixin],
    force: bool = False,
    on_result: Optional[Any] = None,
) -> List[GenerationResult]:
    """Generate images for many objects.

    :param on_result: An optional callable receiving ``(obj, result)`` after
        each object, for progress reporting.
    :returns: One :class:`GenerationResult` per object, in order.
    """
    results: List[GenerationResult] = []

    for obj in objects:
        result = generate_result(obj, force=force)
        results.append(result)

        if on_result is not None:
            on_result(obj, result)

    return results


def _persist(obj: OpenGraphImageMixin, url: str, digest: str) -> None:
    """Write the result back without firing ``post_save`` again."""
    obj.og_image_url = url
    obj.og_image_hash = digest

    type(obj)._default_manager.filter(pk=obj.pk).update(
        og_image_url=url,
        og_image_hash=digest,
    )
