"""Access to the underlying html2img API client.

The package talks to the API through the official
`html2img-client <https://pypi.org/project/html2img-client/>`_ SDK. Everything
goes through :func:`get_client`, so a project can substitute its own configured
client, for retry middleware, a proxy or request logging.
"""

from __future__ import annotations

from typing import Optional

from django.core.exceptions import ImproperlyConfigured
from html2img import Html2img

from html2img_django import conf

__all__ = ["get_client", "reset_client", "set_client"]

_override: Optional[Html2img] = None


def set_client(client: Optional[Html2img]) -> None:
    """Use this client for every render instead of building one from settings.

    .. code-block:: python

        # apps.py
        from html2img import Html2img
        from html2img_django.client import set_client

        set_client(Html2img(transport=my_retrying_transport))

    Pass ``None`` to go back to the settings-built client.
    """
    global _override

    _override = client


def reset_client() -> None:
    """Drop any client set with :func:`set_client`."""
    set_client(None)


def get_client() -> Html2img:
    """The client to render with.

    :raises django.core.exceptions.ImproperlyConfigured: if no API key is
        configured.
    """
    if _override is not None:
        return _override

    key = conf.api_key()

    if not key:
        raise ImproperlyConfigured(
            "No html2img API key. Set the HTML2IMG_API_KEY environment variable, "
            "or HTML2IMG['API_KEY'] in your settings. Create a free key at "
            "https://app.html2img.com/register."
        )

    return Html2img(
        api_key=key,
        base_url=conf.get_setting("BASE_URL"),
        timeout=float(conf.get_setting("TIMEOUT")),
    )
