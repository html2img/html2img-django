"""Automatic Open Graph images for Django, rendered by the HTML to Image API.

Design the card as an ordinary Django template, register the models that should
have one, and every save renders the card in real Chrome and stores the
resulting image URL on the object.

.. code-block:: python

    # blog/og_images.py
    from html2img_django import og_images

    from .models import Post

    og_images.register(Post, template="og/post.html")

Documentation: https://html2img.com/docs
"""

from __future__ import annotations

__version__ = "1.0.1"

__all__ = [
    "GenerationResult",
    "OpenGraphImageMixin",
    "__version__",
    "generate",
    "generate_result",
    "og_images",
]


def __getattr__(name: str) -> object:
    """Expose the public API without importing Django models at package import.

    Django forbids importing models before the app registry is ready, and this
    package is imported from ``settings.py`` territory, so the model mixin and
    anything touching it are resolved lazily.
    """
    if name == "og_images":
        from html2img_django.registry import og_images

        return og_images

    if name == "OpenGraphImageMixin":
        from html2img_django.models import OpenGraphImageMixin

        return OpenGraphImageMixin

    if name in {"GenerationResult", "generate", "generate_result"}:
        from html2img_django import generator

        return getattr(generator, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
