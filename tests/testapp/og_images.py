"""Registrations, auto-discovered when the app registry is ready."""

from __future__ import annotations

from html2img_django import og_images

from .models import Page, Post

og_images.register(Post)
og_images.register(
    Page,
    template="og/page.html",
    width=800,
    height=418,
    dpi=1,
    context=lambda page: {"og_subtitle": f"Page: {page.name}"},
)
