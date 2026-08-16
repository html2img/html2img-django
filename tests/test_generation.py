"""The generation pipeline."""

from __future__ import annotations

import pytest
from django.test import override_settings

from html2img_django.generator import generate, generate_result
from html2img_django.rendering import build_context, fingerprint, render_card, settings_for
from tests.conftest import FakeTransport
from tests.testapp.models import Page, Post

pytestmark = pytest.mark.django_db


def test_it_renders_and_stores_the_url(post: Post, transport: FakeTransport) -> None:
    url = generate(post)

    assert url == "https://i.html2img.com/abc123.png"

    post.refresh_from_db()

    assert post.og_image_url == "https://i.html2img.com/abc123.png"
    assert post.og_image_hash != ""


def test_it_posts_the_rendered_card_at_the_configured_size(
    post: Post, transport: FakeTransport
) -> None:
    generate(post)

    body = transport.last["body"]

    assert transport.last["url"].endswith("/api/html")
    assert body["width"] == 1200
    assert body["height"] == 630
    assert body["dpi"] == 2
    assert body["format"] == "png"
    assert "Real Chrome rendering" in body["html"]
    assert "Jamie Rivera" in body["html"]


def test_it_skips_a_render_when_the_inputs_are_unchanged(
    post: Post, transport: FakeTransport
) -> None:
    generate(post)
    generate(post)

    assert transport.count == 1


def test_force_re_renders_unchanged_inputs(post: Post, transport: FakeTransport) -> None:
    generate(post)
    generate(post, force=True)

    assert transport.count == 2


def test_changing_the_content_triggers_a_new_render(post: Post, transport: FakeTransport) -> None:
    generate(post)
    post.title = "A different headline"
    post.save()
    generate(post)

    assert transport.count == 2


def test_it_skips_objects_that_opted_out(post: Post, transport: FakeTransport) -> None:
    post.og_image_disabled = True

    assert generate(post) is None
    assert transport.count == 0


def test_it_skips_objects_with_a_custom_image(post: Post, transport: FakeTransport) -> None:
    post.og_image_custom = "https://example.com/custom.png"

    assert generate(post) is None
    assert transport.count == 0


def test_it_uses_the_per_model_registration_options(db, transport: FakeTransport) -> None:
    page = Page.objects.create(name="Pricing")

    generate(page)

    body = transport.last["body"]

    assert body["width"] == 800
    assert body["height"] == 418
    assert body["dpi"] == 1
    assert "Page: Pricing" in body["html"]  # from the registered context callable
    assert "<h1>Pricing</h1>" in body["html"]  # from the per-model template


def test_an_api_failure_leaves_the_object_untouched(post: Post, transport: FakeTransport) -> None:
    transport.queued = [(402, {"error": "Out of credits.", "code": "insufficient_credits"})]

    assert generate(post) is None

    post.refresh_from_db()

    assert post.og_image_url == ""


def test_a_missing_url_is_not_stored(post: Post, transport: FakeTransport) -> None:
    transport.queued = [(200, {"success": True, "status": "processing"})]

    assert generate(post) is None

    post.refresh_from_db()

    assert post.og_image_url == ""


@override_settings(HTML2IMG={"API_KEY": "test-key", "ENABLED": False})
def test_it_does_nothing_when_disabled(post: Post, transport: FakeTransport) -> None:
    assert generate(post) is None
    assert transport.count == 0


def test_it_ignores_unsaved_objects(db, transport: FakeTransport) -> None:
    assert generate(Post(title="Unsaved")) is None
    assert transport.count == 0


class TestGenerationResult:
    """`generate_result` distinguishes a real render from a reused image."""

    def test_a_first_render_reports_itself_as_rendered(self, post: Post) -> None:
        result = generate_result(post)

        assert result.rendered is True
        assert result.reused is False
        assert result.ok is True
        assert result.reason is None

    def test_an_unchanged_object_reports_itself_as_reused(
        self, post: Post, transport: FakeTransport
    ) -> None:
        generate_result(post)
        result = generate_result(post)

        assert result.rendered is False
        assert result.reused is True
        assert result.ok is True
        assert transport.count == 1

    def test_an_opted_out_object_reports_why(self, post: Post) -> None:
        post.og_image_disabled = True
        result = generate_result(post)

        assert result.reason == "opted-out"
        assert result.ok is False

    def test_an_api_failure_reports_why(self, post: Post, transport: FakeTransport) -> None:
        transport.queued = [(500, {"error": "Renderer exploded."})]

        assert generate_result(post).reason == "error"

    def test_an_async_acceptance_reports_why(self, post: Post, transport: FakeTransport) -> None:
        transport.queued = [(200, {"success": True, "status": "processing"})]

        assert generate_result(post).reason == "no-url"


class TestMediaStorage:
    """``STORAGE = "media"`` downloads the render into Django's storage.

    These use the pytest-django ``settings`` fixture rather than
    ``override_settings``, because mixing the two in one test leaks state into
    the tests that follow.
    """

    @staticmethod
    def _use_media_storage(settings, tmp_path) -> None:
        settings.HTML2IMG = {"API_KEY": "test-key", "SITE_NAME": "Example", "STORAGE": "media"}
        settings.MEDIA_URL = "/media/"
        settings.MEDIA_ROOT = tmp_path

    def test_it_downloads_the_render_into_django_storage(
        self, post: Post, transport: FakeTransport, tmp_path, settings
    ) -> None:
        self._use_media_storage(settings, tmp_path)
        transport.queued = [
            (200, {"success": True, "url": "https://i.html2img.com/a.png"}),
            (200, b"png-bytes"),
        ]

        url = generate(post)

        assert url == f"/media/og-images/testapp/post/{post.pk}.png"

        stored = tmp_path / "og-images" / "testapp" / "post" / f"{post.pk}.png"

        assert stored.read_bytes() == b"png-bytes"

    def test_it_falls_back_to_the_cdn_url_when_the_download_fails(
        self, post: Post, transport: FakeTransport, tmp_path, settings
    ) -> None:
        self._use_media_storage(settings, tmp_path)
        transport.queued = [
            (200, {"success": True, "url": "https://i.html2img.com/a.png"}),
            (500, b""),
        ]

        assert generate(post) == "https://i.html2img.com/a.png"


class TestRendering:
    def test_the_context_carries_the_object_and_the_site_details(self, post: Post) -> None:
        context = build_context(post)

        assert context["object"] is post
        assert context["post"] is post
        assert context["og_headline"] == "Real Chrome rendering"
        assert context["site_name"] == "Example"
        assert context["author"] == "Jamie Rivera"  # from og_image_context()

    def test_an_explicit_headline_wins_over_the_title(self, post: Post) -> None:
        post.og_image_headline = "Custom headline"

        assert build_context(post)["og_headline"] == "Custom headline"

    def test_the_card_renders_to_html(self, post: Post) -> None:
        html = render_card(post)

        assert html.startswith("<!doctype html>")
        assert "Real Chrome rendering" in html

    def test_the_fingerprint_changes_with_the_content(self, post: Post) -> None:
        resolved = settings_for(post)
        first = fingerprint(render_card(post, resolved), resolved)

        post.title = "Something else"
        second = fingerprint(render_card(post, resolved), resolved)

        assert first != second

    def test_the_fingerprint_changes_with_the_dimensions(self, post: Post) -> None:
        resolved = settings_for(post)
        html = render_card(post, resolved)

        from dataclasses import replace

        assert fingerprint(html, resolved) != fingerprint(html, replace(resolved, width=600))
