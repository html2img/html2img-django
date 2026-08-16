"""A one-command health check for the integration."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.template import TemplateDoesNotExist
from django.template.loader import get_template
from html2img import Html2imgError

from html2img_django import conf
from html2img_django.client import get_client
from html2img_django.registry import og_images

TEST_DOCUMENT = (
    '<!doctype html><html><body style="font-family:system-ui;display:flex;'
    "align-items:center;justify-content:center;height:180px;margin:0;"
    'background:#0f172a;color:#fff"><h1>html2img is configured</h1></body></html>'
)


class Command(BaseCommand):
    """Check the settings, the card template and the API key, then render once."""

    help = "Verify the html2img configuration by rendering a small test image (uses one credit)."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--no-render",
            action="store_true",
            help="Check the configuration without calling the API.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        self._report_settings()
        self._report_registry()
        self._report_template()

        if not conf.api_key():
            raise CommandError(
                "No API key. Set HTML2IMG_API_KEY in your environment, or "
                "HTML2IMG['API_KEY'] in settings. Create a free key at "
                "https://app.html2img.com/register."
            )

        if options["no_render"]:
            self.stdout.write(self.style.SUCCESS("Configuration looks good."))

            return

        self._render()

    def _report_settings(self) -> None:
        resolved = conf.resolve()

        self.stdout.write(f"Template:  {resolved.template}")
        self.stdout.write(f"Size:      {resolved.width}x{resolved.height} @ {resolved.dpi}x")
        self.stdout.write(f"Format:    {resolved.format}")
        self.stdout.write(f"Storage:   {resolved.storage}")
        self.stdout.write(f"On save:   {conf.on_save_mode()}")
        self.stdout.write(f"Enabled:   {conf.get_setting('ENABLED')}")

    def _report_registry(self) -> None:
        if not len(og_images):
            self.stdout.write(
                self.style.WARNING(
                    "Models:    none registered. Add og_images.register(YourModel) to an "
                    "og_images.py module in one of your apps."
                )
            )

            return

        labels = ", ".join(sorted(model._meta.label for model in og_images.models()))
        self.stdout.write(f"Models:    {labels}")

    def _report_template(self) -> None:
        template = conf.resolve().template

        try:
            get_template(template)
        except TemplateDoesNotExist:
            self.stdout.write(self.style.ERROR(f"Template {template} could not be found."))

    def _render(self) -> None:
        self.stdout.write("Rendering a test image via the html2img API...")

        try:
            response = get_client().html(TEST_DOCUMENT, width=600, height=200)
        except Html2imgError as error:
            raise CommandError(f"Request failed: {error}") from error

        self.stdout.write(self.style.SUCCESS("Test render succeeded."))
        self.stdout.write(f"Image URL: {response.url}")

        if response.credits_remaining is not None:
            self.stdout.write(f"Credits remaining: {response.credits_remaining}")
