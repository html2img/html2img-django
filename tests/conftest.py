"""Shared fixtures.

Every test drives the package through a fake transport, so the suite never
touches the network and never spends a credit.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

import pytest
from html2img import Html2img

from html2img_django import client as client_module

RENDERED = {
    "success": True,
    "id": "abc123",
    "url": "https://i.html2img.com/abc123.png",
    "credits_remaining": 49,
}


class FakeTransport:
    """Records calls and replays queued responses."""

    def __init__(self, *responses: Tuple[int, Any]) -> None:
        self.queued: List[Tuple[int, Any]] = list(responses) or [(200, RENDERED)]
        self.calls: List[Dict[str, Any]] = []

    def __call__(
        self,
        *,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: Optional[bytes],
        timeout: float,
    ) -> Tuple[int, bytes]:
        self.calls.append(
            {
                "method": method,
                "url": url,
                "body": json.loads(body.decode("utf-8")) if body else None,
            }
        )

        status, payload = self.queued.pop(0) if len(self.queued) > 1 else self.queued[0]

        if isinstance(payload, bytes):
            return status, payload

        return status, json.dumps(payload).encode("utf-8")

    @property
    def last(self) -> Dict[str, Any]:
        return self.calls[-1]

    @property
    def count(self) -> int:
        return len(self.calls)


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture(autouse=True)
def fake_client(transport: FakeTransport):
    """Point the package at a client that never leaves the process."""
    client_module.set_client(Html2img("test-key", transport=transport))

    yield transport

    client_module.reset_client()


@pytest.fixture
def post(db):
    from tests.testapp.models import Post

    return Post.objects.create(title="Real Chrome rendering", author="Jamie Rivera")


@pytest.fixture
def staff_client(db, client):
    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(
        username="editor", password="password", is_staff=True
    )
    client.force_login(user)

    return client
