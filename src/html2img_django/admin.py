"""Admin helpers: a live preview, the generated image, and a regenerate action.

Mix :class:`OpenGraphImageAdminMixin` into a ``ModelAdmin`` to get all three:

.. code-block:: python

    from django.contrib import admin
    from html2img_django.admin import OpenGraphImageAdminMixin

    from .models import Post

    @admin.register(Post)
    class PostAdmin(OpenGraphImageAdminMixin, admin.ModelAdmin):
        list_display = ("title", "og_image_status")

The preview panel needs the package's URLs to be included; see
:mod:`html2img_django.urls`.
"""

from __future__ import annotations

from typing import Any, List, Optional, Sequence

from django.contrib import admin, messages
from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.safestring import SafeString, mark_safe
from django.utils.translation import gettext_lazy as _

from html2img_django.generator import generate
from html2img_django.rendering import settings_for

__all__ = ["OpenGraphImageAdminMixin"]

PREVIEW_WIDTH = 480


class OpenGraphImageAdminMixin:
    """Adds Open Graph tooling to a ``ModelAdmin``.

    - ``og_image_status``: a changelist column showing the state of the image.
    - ``og_image_preview``: a readonly field showing the live template preview
      next to the last rendered image.
    - a "Regenerate Open Graph images" action.
    """

    og_image_readonly_fields: Sequence[str] = ("og_image_preview",)

    actions = ["regenerate_og_images"]

    def get_readonly_fields(
        self, request: HttpRequest, obj: Optional[Model] = None
    ) -> Sequence[str]:
        fields = list(super().get_readonly_fields(request, obj))  # type: ignore[misc]

        for name in self.og_image_readonly_fields:
            if name not in fields:
                fields.append(name)

        return fields

    @admin.display(description=_("OG image"))
    def og_image_status(self, obj: Any) -> Any:
        """A short status for the changelist."""
        if obj.og_image_disabled:
            return _("Disabled")

        if obj.get_og_custom_image():
            return _("Custom")

        return _("Generated") if obj.og_image_url else _("Not generated")

    @admin.display(description=_("Open Graph image"))
    def og_image_preview(self, obj: Optional[Any] = None) -> SafeString:
        """The live template preview alongside the last rendered image."""
        if obj is None or obj.pk is None:
            return format_html("<p>{}</p>", _("Save this object to preview its card."))

        panels: List[SafeString] = []
        preview_url = _preview_url(obj)

        if preview_url:
            resolved = settings_for(obj)
            height = int(resolved.height * (PREVIEW_WIDTH / resolved.width))

            panels.append(
                format_html(
                    "<div><p><strong>{}</strong></p>"
                    '<iframe src="{}" loading="lazy" '
                    'style="width:{}px;height:{}px;border:1px solid #ddd;background:#fff">'
                    "</iframe></div>",
                    _("Template preview"),
                    preview_url,
                    PREVIEW_WIDTH,
                    height,
                )
            )

        if obj.og_image_url:
            panels.append(
                format_html(
                    "<div><p><strong>{}</strong></p>"
                    '<img src="{}" alt="" style="width:{}px;height:auto;border:1px solid #ddd">'
                    '<p><a href="{}" target="_blank" rel="noopener">{}</a></p></div>',
                    _("Last render"),
                    obj.og_image_url,
                    PREVIEW_WIDTH,
                    obj.og_image_url,
                    _("Open the rendered file"),
                )
            )

        if not panels:
            return format_html("<p>{}</p>", _("No image yet. Save this object to generate one."))

        return format_html(
            '<div style="display:flex;gap:24px;flex-wrap:wrap">{}</div>',
            mark_safe("".join(panels)),  # every panel came from format_html, so it is escaped
        )

    @admin.action(description=_("Regenerate Open Graph images"))
    def regenerate_og_images(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Force a re-render for the selected objects."""
        generated = sum(1 for obj in queryset if generate(obj, force=True))

        self.message_user(  # type: ignore[attr-defined]
            request,
            _("Regenerated %(count)d Open Graph image(s).") % {"count": generated},
            messages.SUCCESS if generated else messages.WARNING,
        )


def _preview_url(obj: Model) -> str:
    """The staff-only preview URL for an object, or an empty string if not routed."""
    try:
        return reverse(
            "html2img_django:preview-object",
            kwargs={"label": obj._meta.label, "pk": obj.pk},
        )
    except NoReverseMatch:
        return ""
