"""The `og_image` template tags."""

from __future__ import annotations

import pytest
from django.template import Context, Template
from django.test import override_settings

from tests.testapp.models import Post

pytestmark = pytest.mark.django_db


def render(template: str, **context) -> str:
    return Template("{% load og_image %}" + template).render(Context(context)).strip()


class TestUrlTag:
    def test_it_returns_the_generated_image(self, post: Post) -> None:
        post.og_image_url = "https://i.html2img.com/generated.png"

        assert render("{% og_image_url object %}", object=post) == (
            "https://i.html2img.com/generated.png"
        )

    def test_a_custom_image_wins_over_the_generated_one(self, post: Post) -> None:
        post.og_image_url = "https://i.html2img.com/generated.png"
        post.og_image_custom = "https://example.com/custom.png"

        assert render("{% og_image_url object %}", object=post) == "https://example.com/custom.png"

    @override_settings(
        HTML2IMG={"API_KEY": "k", "DEFAULT_IMAGE": "https://example.com/fallback.png"}
    )
    def test_it_falls_back_to_the_site_default(self, post: Post) -> None:
        assert render("{% og_image_url object %}", object=post) == (
            "https://example.com/fallback.png"
        )

    @override_settings(
        HTML2IMG={"API_KEY": "k", "DEFAULT_IMAGE": "https://example.com/fallback.png"}
    )
    def test_it_works_with_no_object_at_all(self) -> None:
        assert render("{% og_image_url %}") == "https://example.com/fallback.png"

    def test_it_returns_nothing_when_there_is_no_image(self, post: Post) -> None:
        assert render("{% og_image_url object %}", object=post) == ""


class TestMetaTag:
    def test_it_writes_the_open_graph_and_twitter_tags(self, post: Post) -> None:
        post.og_image_url = "https://i.html2img.com/generated.png"

        output = render("{% og_image_meta object %}", object=post)

        assert '<meta property="og:image" content="https://i.html2img.com/generated.png">' in output
        assert '<meta property="og:image:width" content="1200">' in output
        assert '<meta property="og:image:height" content="630">' in output
        assert '<meta property="og:image:type" content="image/png">' in output
        assert '<meta property="og:image:alt" content="Real Chrome rendering">' in output
        assert '<meta name="twitter:card" content="summary_large_image">' in output
        assert (
            '<meta name="twitter:image" content="https://i.html2img.com/generated.png">' in output
        )

    def test_it_writes_nothing_when_there_is_no_image(self, post: Post) -> None:
        assert render("{% og_image_meta object %}", object=post) == ""

    def test_it_escapes_the_alt_text(self, post: Post) -> None:
        post.title = 'Quote " and <script>'
        post.og_image_url = "https://i.html2img.com/generated.png"

        output = render("{% og_image_meta object %}", object=post)

        assert "<script>" not in output
        assert "&lt;script&gt;" in output

    def test_it_uses_the_per_model_dimensions(self, db) -> None:
        from tests.testapp.models import Page

        page = Page.objects.create(name="Pricing")
        page.og_image_url = "https://i.html2img.com/page.png"

        output = render("{% og_image_meta object %}", object=page)

        assert '<meta property="og:image:width" content="800">' in output
        assert '<meta property="og:image:height" content="418">' in output
