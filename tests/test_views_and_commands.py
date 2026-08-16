"""The preview views, the management commands and the admin mixin."""

from __future__ import annotations

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from django.test import override_settings

from tests.conftest import FakeTransport
from tests.testapp.models import Post

pytestmark = pytest.mark.django_db


class TestPreview:
    def test_it_is_closed_to_anonymous_visitors(self, client) -> None:
        response = client.get("/og-images/preview/")

        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    def test_the_sample_preview_renders_the_default_card(self, staff_client) -> None:
        response = staff_client.get("/og-images/preview/")

        assert response.status_code == 200
        assert b"How real Chrome rendering changes social images" in response.content

    def test_it_renders_a_real_object(self, staff_client, post: Post) -> None:
        response = staff_client.get(f"/og-images/preview/testapp.Post/{post.pk}/")

        assert response.status_code == 200
        assert b"Real Chrome rendering" in response.content

    def test_an_unregistered_model_is_a_404(self, staff_client) -> None:
        assert staff_client.get("/og-images/preview/testapp.Plain/1/").status_code == 404

    def test_a_missing_object_is_a_404(self, staff_client) -> None:
        assert staff_client.get("/og-images/preview/testapp.Post/999/").status_code == 404


class TestGenerateCommand:
    def test_it_generates_across_registered_models(
        self, post: Post, transport: FakeTransport
    ) -> None:
        out = StringIO()
        call_command("generate_og_images", stdout=out, stderr=StringIO())

        assert transport.count == 1
        assert "1 rendered" in out.getvalue()

        post.refresh_from_db()

        assert post.og_image_url == "https://i.html2img.com/abc123.png"

    def test_it_can_target_one_model(self, post: Post, transport: FakeTransport) -> None:
        out = StringIO()
        call_command("generate_og_images", "--model", "testapp.Post", stdout=out)

        assert transport.count == 1

    def test_it_rejects_an_unknown_model(self, post: Post) -> None:
        with pytest.raises(CommandError, match="No Open Graph model registered"):
            call_command("generate_og_images", "--model", "testapp.Nope", stdout=StringIO())

    def test_a_dry_run_calls_nothing(self, post: Post, transport: FakeTransport) -> None:
        out = StringIO()
        call_command("generate_og_images", "--dry-run", stdout=out)

        assert transport.count == 0
        assert "would render" in out.getvalue()

    def test_it_skips_unchanged_objects_without_force(
        self, post: Post, transport: FakeTransport
    ) -> None:
        call_command("generate_og_images", stdout=StringIO())

        out = StringIO()
        call_command("generate_og_images", stdout=out)

        assert transport.count == 1
        assert "0 rendered, 1 unchanged" in out.getvalue()

    def test_it_reports_objects_that_opted_out(self, post: Post, transport: FakeTransport) -> None:
        post.og_image_disabled = True
        post.save(update_fields=["og_image_disabled"])

        out = StringIO()
        call_command("generate_og_images", stdout=out)

        assert transport.count == 0
        assert "1 skipped" in out.getvalue()

    def test_force_re_renders_everything(self, post: Post, transport: FakeTransport) -> None:
        call_command("generate_og_images", stdout=StringIO())
        call_command("generate_og_images", "--force", stdout=StringIO())

        assert transport.count == 2

    def test_it_honours_a_limit(self, db, transport: FakeTransport) -> None:
        Post.objects.bulk_create([Post(title=f"Post {index}") for index in range(3)])

        call_command("generate_og_images", "--limit", "2", stdout=StringIO())

        assert transport.count == 2

    @override_settings(HTML2IMG={"API_KEY": "test-key", "ENABLED": False})
    def test_it_refuses_to_run_when_disabled(self, post: Post) -> None:
        with pytest.raises(CommandError, match="disabled"):
            call_command("generate_og_images", stdout=StringIO())


class TestHealthCheckCommand:
    def test_it_reports_the_configuration_without_rendering(self, transport: FakeTransport) -> None:
        out = StringIO()
        call_command("html2img_test", "--no-render", stdout=out)

        output = out.getvalue()

        assert "html2img_django/default.html" in output
        assert "1200x630 @ 2x" in output
        assert "testapp.Post" in output
        assert "Configuration looks good." in output
        assert transport.count == 0

    def test_it_renders_a_test_image(self, transport: FakeTransport) -> None:
        out = StringIO()
        call_command("html2img_test", stdout=out)

        assert transport.count == 1
        assert "Test render succeeded." in out.getvalue()
        assert "https://i.html2img.com/abc123.png" in out.getvalue()

    def test_it_reports_a_failed_render(self, transport: FakeTransport) -> None:
        transport.queued = [(401, {"error": "Invalid API key.", "code": "invalid_api_key"})]

        with pytest.raises(CommandError, match="Invalid API key"):
            call_command("html2img_test", stdout=StringIO())


class TestAdminMixin:
    def test_the_status_column_reflects_the_object(self, post: Post) -> None:
        from django.contrib import admin

        from html2img_django.admin import OpenGraphImageAdminMixin

        class PostAdmin(OpenGraphImageAdminMixin, admin.ModelAdmin):
            pass

        model_admin = PostAdmin(Post, admin.site)

        assert str(model_admin.og_image_status(post)) == "Not generated"

        post.og_image_url = "https://i.html2img.com/a.png"
        assert str(model_admin.og_image_status(post)) == "Generated"

        post.og_image_custom = "https://example.com/c.png"
        assert str(model_admin.og_image_status(post)) == "Custom"

        post.og_image_disabled = True
        assert str(model_admin.og_image_status(post)) == "Disabled"

    def test_the_preview_panel_links_to_the_preview_route(self, post: Post) -> None:
        from django.contrib import admin

        from html2img_django.admin import OpenGraphImageAdminMixin

        class PostAdmin(OpenGraphImageAdminMixin, admin.ModelAdmin):
            pass

        html = PostAdmin(Post, admin.site).og_image_preview(post)

        assert f"/og-images/preview/testapp.Post/{post.pk}/" in html

    def test_the_readonly_fields_include_the_preview(self) -> None:
        from django.contrib import admin

        from html2img_django.admin import OpenGraphImageAdminMixin

        class PostAdmin(OpenGraphImageAdminMixin, admin.ModelAdmin):
            pass

        fields = PostAdmin(Post, admin.site).get_readonly_fields(request=None)

        assert "og_image_preview" in fields
