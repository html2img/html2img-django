"""The abstract model that stores a generated Open Graph image."""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ["OpenGraphImageMixin"]


class OpenGraphImageMixin(models.Model):
    """Adds the fields and hooks an Open Graph image needs.

    Inherit from it alongside ``models.Model`` and run ``makemigrations``:

    .. code-block:: python

        from django.db import models
        from html2img_django import OpenGraphImageMixin

        class Post(OpenGraphImageMixin, models.Model):
            title = models.CharField(max_length=200)
            excerpt = models.TextField(blank=True)

    Every field is optional in day-to-day use: the generated URL and its input
    hash are managed for you, and the rest are editor-facing overrides.
    """

    og_image_url = models.URLField(
        _("Open Graph image URL"),
        max_length=500,
        blank=True,
        default="",
        editable=False,
        help_text=_("The generated image. Managed automatically."),
    )
    og_image_hash = models.CharField(
        max_length=40,
        blank=True,
        default="",
        editable=False,
        help_text=_("Fingerprint of the inputs the current image was rendered from."),
    )
    og_image_custom = models.URLField(
        _("custom Open Graph image"),
        max_length=500,
        blank=True,
        default="",
        help_text=_("Use this image instead of generating one. Leave blank to generate."),
    )
    og_image_headline = models.CharField(
        _("Open Graph headline"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Overrides the headline on the image. Defaults to the object's title."),
    )
    og_image_subtitle = models.CharField(
        _("Open Graph subtitle"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Optional second line on the image."),
    )
    og_image_disabled = models.BooleanField(
        _("skip Open Graph image"),
        default=False,
        help_text=_("Never generate an image for this object."),
    )

    class Meta:
        abstract = True

    # ------------------------------------------------------------------
    # Hooks you can override
    # ------------------------------------------------------------------

    def og_image_context(self) -> Dict[str, Any]:
        """Extra template context for this object's card.

        The template already receives ``object``, ``og_headline``,
        ``og_subtitle``, ``site_name`` and ``site_logo``. Override this to add
        anything else your design needs:

        .. code-block:: python

            def og_image_context(self):
                return {"author": self.author.get_full_name(), "reading_time": self.minutes}
        """
        return {}

    def og_image_headline_text(self) -> str:
        """The headline rendered on the card.

        Defaults to the ``og_image_headline`` override, then a ``title``
        attribute, then ``str(self)``.
        """
        if self.og_image_headline:
            return self.og_image_headline

        title = getattr(self, "title", None)

        if isinstance(title, str) and title:
            return title

        return str(self)

    def og_image_subtitle_text(self) -> str:
        """The subtitle rendered on the card. Empty by default."""
        return self.og_image_subtitle

    def get_og_custom_image(self) -> str:
        """A custom image that bypasses generation entirely.

        Defaults to the ``og_image_custom`` URL field. Override it to point at
        an uploaded file instead:

        .. code-block:: python

            def get_og_custom_image(self):
                return self.cover.url if self.cover else ""
        """
        return self.og_image_custom

    def should_generate_og_image(self) -> bool:
        """Whether this object should get a generated image.

        Skips objects that opted out and objects with a custom image.
        """
        return not self.og_image_disabled and not self.get_og_custom_image()

    # ------------------------------------------------------------------
    # Reading the result
    # ------------------------------------------------------------------

    def get_og_image_url(self) -> str:
        """The image URL for this object, resolved through the cascade.

        A custom image first, then the generated one, then the project-wide
        fallback (``HTML2IMG["DEFAULT_IMAGE"]``). Empty string when there is
        nothing to show.
        """
        from html2img_django import conf

        custom = self.get_og_custom_image()

        if custom:
            return str(custom)

        if self.og_image_url:
            return self.og_image_url

        return str(conf.get_setting("DEFAULT_IMAGE") or "")

    def og_image_alt(self) -> str:
        """The ``og:image:alt`` text. Defaults to the headline."""
        return self.og_image_headline_text()

    def generate_og_image(self, force: bool = False) -> Optional[str]:
        """Render this object's image now and store the result.

        Returns the stored URL, or ``None`` when nothing was rendered.
        """
        from html2img_django.generator import generate

        return generate(self, force=force)
