"""Models used by the test suite."""

from __future__ import annotations

from typing import Any, Dict

from django.db import models

from html2img_django.models import OpenGraphImageMixin


class Post(OpenGraphImageMixin, models.Model):
    """A blog post with an Open Graph image."""

    title = models.CharField(max_length=200)
    excerpt = models.TextField(blank=True, default="")
    author = models.CharField(max_length=100, blank=True, default="")

    def __str__(self) -> str:
        return self.title

    def og_image_context(self) -> Dict[str, Any]:
        return {"author": self.author}


class Page(OpenGraphImageMixin, models.Model):
    """A model registered with per-model overrides."""

    name = models.CharField(max_length=200)

    def __str__(self) -> str:
        return self.name


class Plain(models.Model):
    """A model that is not set up for Open Graph images at all."""

    name = models.CharField(max_length=200)
