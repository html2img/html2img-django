"""Bulk regeneration across registered models."""

from __future__ import annotations

from typing import Any, Optional

from django.core.management.base import BaseCommand, CommandError

from html2img_django import conf
from html2img_django.generator import generate_result
from html2img_django.registry import og_images


class Command(BaseCommand):
    """Regenerate Open Graph images. Run it after changing a card template."""

    help = "Generate Open Graph images for registered models."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--model",
            action="append",
            dest="models",
            metavar="app_label.ModelName",
            help="Limit to these models. Repeatable. Defaults to every registered model.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-render even when the inputs are unchanged.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Stop after this many objects per model.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be rendered without calling the API.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if not conf.is_enabled():
            raise CommandError(
                "Rendering is disabled or no API key is set. Set HTML2IMG_API_KEY, "
                "and check HTML2IMG['ENABLED']."
            )

        models = self._models(options.get("models"))

        if not models:
            raise CommandError(
                "No models are registered. Add og_images.register(YourModel) to an "
                "og_images.py module in one of your apps."
            )

        force = bool(options["force"])
        dry_run = bool(options["dry_run"])
        limit: Optional[int] = options["limit"]
        rendered = reused = skipped = failed = 0

        for model in models:
            queryset = og_images.queryset_for(model)

            if limit:
                queryset = queryset[:limit]

            total = queryset.count() if hasattr(queryset, "count") else len(queryset)
            self.stdout.write(f"{model._meta.label}: {total} object(s)")

            for obj in queryset:
                if not obj.should_generate_og_image():
                    skipped += 1
                    self.stdout.write(f"  {obj}: skipped (opted out or has a custom image)")
                    continue

                if dry_run:
                    self.stdout.write(f"  {obj}: would render")
                    rendered += 1
                    continue

                result = generate_result(obj, force=force)

                if result.rendered:
                    rendered += 1
                    self.stdout.write(f"  {obj}: {result.url}")
                elif result.reused:
                    reused += 1
                    self.stdout.write(f"  {obj}: unchanged, kept {result.url}")
                else:
                    failed += 1
                    self.stderr.write(f"  {obj}: no image ({result.reason}); see the log")

        summary = (
            f"Done. {rendered} rendered, {reused} unchanged, {skipped} skipped, {failed} failed."
        )
        style = self.style.WARNING if failed else self.style.SUCCESS

        self.stdout.write(style(summary))

        if reused and not force:
            self.stdout.write(
                "Unchanged objects cost nothing. Pass --force to re-render them anyway."
            )

    def _models(self, labels: Optional[list]) -> list:
        if not labels:
            return og_images.models()

        try:
            return [og_images.find(label) for label in labels]
        except LookupError as error:
            raise CommandError(str(error)) from error
