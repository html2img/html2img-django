"""The Django app configuration."""

from __future__ import annotations

from django.apps import AppConfig
from django.utils.module_loading import autodiscover_modules
from django.utils.translation import gettext_lazy as _


class Html2imgDjangoConfig(AppConfig):
    """Wires the package up when Django starts.

    On ``ready`` it imports every installed app's ``og_images`` module, the way
    Django imports ``admin`` modules, and connects the save hook.
    """

    name = "html2img_django"
    label = "html2img_django"
    verbose_name = _("Open Graph Images")

    def ready(self) -> None:
        from html2img_django import signals

        autodiscover_modules("og_images")
        signals.connect()
