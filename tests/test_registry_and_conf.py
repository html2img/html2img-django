"""The registry and the settings cascade."""

from __future__ import annotations

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from html2img_django import conf
from html2img_django.registry import Registry, og_images
from tests.testapp.models import Page, Plain, Post


class TestRegistry:
    def test_the_test_app_registrations_were_discovered(self) -> None:
        assert og_images.is_registered(Post)
        assert og_images.is_registered(Page)
        assert not og_images.is_registered(Plain)

    def test_it_records_the_options_a_model_was_registered_with(self) -> None:
        assert og_images.options_for(Page)["width"] == 800
        assert og_images.options_for(Post) == {}

    def test_it_finds_a_model_by_label(self) -> None:
        assert og_images.find("testapp.Post") is Post
        assert og_images.find("testapp.post") is Post

    def test_it_reports_an_unknown_label_clearly(self) -> None:
        with pytest.raises(LookupError, match="No Open Graph model registered"):
            og_images.find("testapp.Nope")

    def test_it_rejects_a_model_without_the_mixin(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="OpenGraphImageMixin"):
            Registry().register(Plain)

    def test_it_rejects_something_that_is_not_a_model(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="not a Django model"):
            Registry().register(dict)

    def test_it_rejects_unknown_options(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="Unknown registration options"):
            Registry().register(Post, colour="red")

    def test_it_works_as_a_decorator(self) -> None:
        registry = Registry()
        decorate = registry.register(width=600)

        assert decorate(Post) is Post
        assert registry.is_registered(Post)
        assert registry.options_for(Post) == {"width": 600}

    def test_unregister_removes_a_model(self) -> None:
        registry = Registry()
        registry.register(Post)
        registry.unregister(Post)

        assert not registry.is_registered(Post)
        assert len(registry) == 0


class TestSettings:
    def test_the_defaults_apply_when_nothing_is_configured(self) -> None:
        resolved = conf.resolve()

        assert resolved.template == "html2img_django/default.html"
        assert (resolved.width, resolved.height, resolved.dpi) == (1200, 630, 2)
        assert resolved.storage == "cdn"

    @override_settings(HTML2IMG={"API_KEY": "k", "WIDTH": 1000, "DPI": 1})
    def test_project_settings_override_the_defaults(self) -> None:
        resolved = conf.resolve()

        assert resolved.width == 1000
        assert resolved.dpi == 1
        assert resolved.height == 630

    @override_settings(HTML2IMG={"API_KEY": "k", "WIDTH": 1000})
    def test_registration_options_override_project_settings(self) -> None:
        resolved = conf.resolve({"width": 800, "template": "og/page.html"})

        assert resolved.width == 800
        assert resolved.template == "og/page.html"

    @override_settings(HTML2IMG={"TYPO": True})
    def test_an_unknown_setting_is_reported(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="Unknown HTML2IMG settings: TYPO"):
            conf.get_setting("WIDTH")

    @override_settings(HTML2IMG=["not", "a", "dict"])
    def test_a_malformed_settings_block_is_reported(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="must be a dict"):
            conf.get_setting("WIDTH")

    @override_settings(HTML2IMG={"API_KEY": "k", "STORAGE": "dropbox"})
    def test_an_invalid_storage_mode_is_reported(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="STORAGE"):
            conf.resolve()

    @override_settings(HTML2IMG={"API_KEY": "k", "ON_SAVE": "later"})
    def test_an_invalid_on_save_mode_is_reported(self) -> None:
        with pytest.raises(ImproperlyConfigured, match="ON_SAVE"):
            conf.on_save_mode()

    @override_settings(HTML2IMG={})
    def test_the_api_key_falls_back_to_the_environment(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HTML2IMG_API_KEY", "from-env")

        assert conf.api_key() == "from-env"
        assert conf.is_enabled() is True

    @override_settings(HTML2IMG={})
    def test_it_is_not_enabled_without_a_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTML2IMG_API_KEY", raising=False)

        assert conf.api_key() is None
        assert conf.is_enabled() is False

    def test_pdf_settings_carry_the_right_extension_and_type(self) -> None:
        resolved = conf.resolve({"format": "pdf"})

        assert resolved.extension == "pdf"
        assert resolved.content_type == "application/pdf"
