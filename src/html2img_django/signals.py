"""Regenerating an image when a registered object is saved.

A single ``post_save`` receiver covers every registered model, so registering a
model later (in an ``og_images.py`` module, or from a test) needs no extra
wiring. The work is deferred to ``transaction.on_commit``, so a render never
runs against a state that then gets rolled back.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Type

from django.db import connections, transaction
from django.db.models import Model
from django.db.models.signals import post_save

from html2img_django import conf
from html2img_django.registry import og_images

logger = logging.getLogger("html2img_django")

DISPATCH_UID = "html2img_django.generate_on_save"

__all__ = ["connect", "disconnect", "handle_save"]


def connect() -> None:
    """Listen for saves on every model. Idempotent."""
    post_save.connect(handle_save, dispatch_uid=DISPATCH_UID)


def disconnect() -> None:
    """Stop listening. Mostly useful in tests."""
    post_save.disconnect(dispatch_uid=DISPATCH_UID)


def handle_save(sender: Type[Model], instance: Any, raw: bool = False, **kwargs: Any) -> None:
    """Queue a render for a saved object, if it needs one."""
    if raw or not og_images.is_registered(sender):
        return

    mode = conf.on_save_mode()

    if mode == "off" or not conf.is_enabled():
        return

    if not instance.should_generate_og_image():
        return

    pk = instance.pk

    if pk is None:  # pragma: no cover - post_save always has a pk
        return

    transaction.on_commit(lambda: _dispatch(sender, pk, mode))


def _dispatch(model: Type[Model], pk: Any, mode: str) -> None:
    if mode == "sync":
        _generate(model, pk)

        return

    thread = threading.Thread(
        target=_generate_in_thread,
        args=(model, pk),
        name=f"html2img-og-{model._meta.label_lower}-{pk}",
        daemon=True,
    )
    thread.start()


def _generate(model: Type[Model], pk: Any) -> None:
    """Load the object fresh and render it.

    Re-fetching by primary key keeps the render honest: it always reflects
    committed state, not whatever the in-memory instance happened to hold.
    """
    from html2img_django.generator import generate

    try:
        obj: Any = model._default_manager.filter(pk=pk).first()

        if obj is None:
            return

        generate(obj)
    except Exception:  # pragma: no cover - a background render must never crash the app
        logger.exception("Open Graph image generation failed for %s %s.", model.__name__, pk)


def _generate_in_thread(model: Type[Model], pk: Any) -> None:
    """Render in a worker thread, releasing its database connections after."""
    try:
        _generate(model, pk)
    finally:
        connections.close_all()
