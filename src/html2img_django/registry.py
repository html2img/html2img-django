"""The registry of models that get an Open Graph image.

Registering a model is the Django equivalent of enabling a collection: saving a
registered object generates its image, and the management command walks every
registered model.

Put your registrations in an ``og_images.py`` module inside any installed app
and they are imported automatically, the same way ``admin.py`` is:

.. code-block:: python

    # blog/og_images.py
    from html2img_django import og_images

    from .models import Post

    og_images.register(Post, template="og/post.html")
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, List, Optional, Type

from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model

VALID_OPTIONS = {
    "template",
    "width",
    "height",
    "dpi",
    "format",
    "storage",
    "media_path",
    "context",
    "queryset",
}


class Registry:
    """Holds the registered models and the options each was registered with."""

    def __init__(self) -> None:
        self._models: Dict[Type[Model], Dict[str, Any]] = {}

    def register(
        self,
        model: Optional[Type[Model]] = None,
        **options: Any,
    ) -> Any:
        """Register a model, optionally overriding the project-wide settings.

        .. code-block:: python

            og_images.register(Post, template="og/post.html", height=800)

            @og_images.register(template="og/product.html")
            class Product(OpenGraphImageMixin, models.Model):
                ...

        :param model: The model class. Omit it to use this as a decorator.
        :param template: The template rendered into the image.
        :param width: Image width in CSS pixels.
        :param height: Image height in CSS pixels.
        :param dpi: Device pixel ratio, 1 to 4.
        :param format: ``"png"`` (default) or ``"pdf"``.
        :param storage: ``"cdn"`` or ``"media"``.
        :param media_path: Path template used when storing into Django storage.
        :param context: A callable taking the object and returning extra
            template context, merged over the object's own context.
        :param queryset: A callable returning the queryset the management
            command should walk. Defaults to ``model._default_manager.all()``.
        """
        unknown = set(options) - VALID_OPTIONS

        if unknown:
            raise ImproperlyConfigured(
                f"Unknown registration options: {', '.join(sorted(unknown))}. "
                f"Valid options are: {', '.join(sorted(VALID_OPTIONS))}."
            )

        if model is None:

            def decorator(cls: Type[Model]) -> Type[Model]:
                self.register(cls, **options)

                return cls

            return decorator

        self._check(model)
        self._models[model] = options

        return model

    def unregister(self, model: Type[Model]) -> None:
        """Remove a model from the registry. A no-op if it was not registered."""
        self._models.pop(model, None)

    def is_registered(self, model: Type[Model]) -> bool:
        """Whether this model generates Open Graph images."""
        return model in self._models

    def options_for(self, model: Type[Model]) -> Dict[str, Any]:
        """The options a model was registered with."""
        return dict(self._models.get(model, {}))

    def context_for(self, model: Type[Model]) -> Optional[Callable[[Any], Dict[str, Any]]]:
        """The extra-context callable a model was registered with, if any."""
        callback = self._models.get(model, {}).get("context")

        return callback if callable(callback) else None

    def queryset_for(self, model: Type[Model]) -> Any:
        """The queryset the management command should walk for this model."""
        callback = self._models.get(model, {}).get("queryset")

        if callable(callback):
            return callback()

        return model._default_manager.all()

    def models(self) -> List[Type[Model]]:
        """Every registered model, in registration order."""
        return list(self._models)

    def find(self, label: str) -> Type[Model]:
        """Look a registered model up by its ``app_label.ModelName`` label.

        :raises LookupError: if no registered model matches.
        """
        wanted = label.lower()

        for model in self._models:
            if model._meta.label_lower == wanted:
                return model

        known = ", ".join(sorted(model._meta.label for model in self._models)) or "none"

        raise LookupError(f"No Open Graph model registered as {label!r}. Registered: {known}.")

    def __iter__(self) -> Iterator[Type[Model]]:
        return iter(self._models)

    def __len__(self) -> int:
        return len(self._models)

    def __contains__(self, model: object) -> bool:
        return model in self._models

    @staticmethod
    def _check(model: Type[Model]) -> None:
        from html2img_django.models import OpenGraphImageMixin

        if not (isinstance(model, type) and issubclass(model, Model)):
            raise ImproperlyConfigured(f"{model!r} is not a Django model.")

        if not issubclass(model, OpenGraphImageMixin):
            raise ImproperlyConfigured(
                f"{model.__name__} must inherit from html2img_django.OpenGraphImageMixin "
                "to store its generated image."
            )


og_images = Registry()
"""The project-wide registry. Import this to register your models."""
