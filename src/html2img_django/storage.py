"""Storing a finished render in Django's file storage.

Used when ``HTML2IMG["STORAGE"]`` is ``"media"``. The rendered file is
downloaded once and written to your default storage, so the public site never
depends on the CDN URL at request time.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from html2img import Html2img, Html2imgError

from html2img_django.conf import ResolvedSettings

logger = logging.getLogger("html2img_django")

__all__ = ["localise", "path_for"]


def path_for(obj: Any, resolved: ResolvedSettings) -> str:
    """Build the storage path for an object's render.

    ``HTML2IMG["MEDIA_PATH"]`` is formatted with ``app_label``, ``model_name``,
    ``pk`` and ``extension``.
    """
    return resolved.media_path.format(
        app_label=obj._meta.app_label,
        model_name=obj._meta.model_name,
        pk=obj.pk,
        extension=resolved.extension,
    )


def localise(
    client: Html2img,
    url: str,
    obj: Any,
    resolved: ResolvedSettings,
) -> Optional[str]:
    """Download a render and store it locally, returning the stored URL.

    Returns ``None`` if the download or the write fails, so the caller can fall
    back to the CDN URL rather than losing the render.
    """
    path = path_for(obj, resolved)

    try:
        contents = client.download(url)
    except Html2imgError as error:
        logger.error("Could not download the render for %s: %s", obj, error)

        return None

    try:
        if default_storage.exists(path):
            default_storage.delete(path)

        stored = default_storage.save(path, ContentFile(contents))

        return default_storage.url(stored)
    except Exception as error:  # pragma: no cover - storage backends vary
        logger.error("Could not store the render for %s: %s", obj, error)

        return None
