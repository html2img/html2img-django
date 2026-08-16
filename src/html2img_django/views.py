"""The preview view.

Renders a card template at its configured size and serves it as a plain HTML
page. No API key and no credits are involved, because your browser renders the
same HTML the API would — which is exactly what makes it a tight design loop.

Access is limited to staff users, since a card template can expose unpublished
content.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpRequest, HttpResponse

from html2img_django import conf
from html2img_django.registry import og_images
from html2img_django.rendering import render_card, render_sample, settings_for

__all__ = ["preview", "preview_object"]


@staff_member_required
def preview(request: HttpRequest) -> HttpResponse:
    """Preview the default card template with sample data."""
    return HttpResponse(render_sample(conf.resolve()))


@staff_member_required
def preview_object(request: HttpRequest, label: str, pk: str) -> HttpResponse:
    """Preview the card for one object, by ``app_label.ModelName`` and primary key."""
    try:
        model = og_images.find(label)
    except LookupError as error:
        raise Http404(str(error)) from error

    obj = model._default_manager.filter(pk=pk).first()

    if obj is None:
        raise Http404(f"No {label} with primary key {pk!r}.")

    return HttpResponse(render_card(obj, settings_for(obj)))
