"""Template tags for outputting the image and its social meta tags.

.. code-block:: html+django

    {% load og_image %}

    <head>
        {% og_image_meta object %}
    </head>

``{% og_image_meta %}`` writes the full set of Open Graph and Twitter tags.
``{% og_image_url %}`` gives you just the URL, for when your project already
has its own meta template or an SEO package to feed.
"""

from __future__ import annotations

from typing import Any, Optional

from django import template
from django.utils.html import format_html, format_html_join
from django.utils.safestring import SafeString, mark_safe

from html2img_django import conf
from html2img_django.rendering import settings_for

register = template.Library()


@register.simple_tag
def og_image_url(obj: Optional[Any] = None) -> str:
    """The Open Graph image URL for an object, or the site-wide fallback.

    Resolves the cascade: a custom image, then the generated one, then
    ``HTML2IMG["DEFAULT_IMAGE"]``. Returns an empty string when there is
    nothing to show.
    """
    if obj is None or not hasattr(obj, "get_og_image_url"):
        return str(conf.get_setting("DEFAULT_IMAGE") or "")

    return obj.get_og_image_url()


@register.simple_tag
def og_image_meta(obj: Optional[Any] = None) -> SafeString:
    """The Open Graph and Twitter image meta tags for an object.

    Outputs nothing at all when there is no image to point at, rather than
    emitting empty tags.
    """
    url = og_image_url(obj)

    if not url:
        return mark_safe("")

    resolved = settings_for(obj) if obj is not None and hasattr(obj, "_meta") else conf.resolve()

    alt = obj.og_image_alt() if obj is not None and hasattr(obj, "og_image_alt") else ""
    alt = alt or conf.site_name()

    properties = [
        ("og:image", url),
        ("og:image:width", str(resolved.width)),
        ("og:image:height", str(resolved.height)),
        ("og:image:type", resolved.content_type),
        ("og:image:alt", alt),
    ]

    names = [
        ("twitter:card", "summary_large_image"),
        ("twitter:image", url),
    ]

    return format_html(
        "{}\n{}",
        format_html_join(
            "\n", '<meta property="{}" content="{}">', ((key, value) for key, value in properties)
        ),
        format_html_join(
            "\n", '<meta name="{}" content="{}">', ((key, value) for key, value in names)
        ),
    )
