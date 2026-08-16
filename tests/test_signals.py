"""Saving a registered object queues a render."""

from __future__ import annotations

import pytest
from django.test import override_settings

from tests.conftest import FakeTransport
from tests.testapp.models import Post

pytestmark = pytest.mark.django_db


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "sync"})
def test_saving_a_registered_object_renders_it(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        post = Post.objects.create(title="Hello")

    assert transport.count == 1

    post.refresh_from_db()

    assert post.og_image_url == "https://i.html2img.com/abc123.png"


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "sync"})
def test_the_render_waits_for_the_commit(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=False) as callbacks:
        Post.objects.create(title="Hello")

    assert transport.count == 0
    assert len(callbacks) == 1


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "off"})
def test_nothing_happens_when_on_save_is_off(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        Post.objects.create(title="Hello")

    assert transport.count == 0


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "sync"})
def test_an_opted_out_object_is_not_rendered(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        Post.objects.create(title="Hello", og_image_disabled=True)

    assert transport.count == 0


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "sync"})
def test_storing_the_result_does_not_trigger_another_render(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    with django_capture_on_commit_callbacks(execute=True):
        Post.objects.create(title="Hello")

    assert transport.count == 1


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "sync"})
def test_an_unregistered_model_is_ignored(
    transport: FakeTransport, django_capture_on_commit_callbacks
) -> None:
    from tests.testapp.models import Plain

    with django_capture_on_commit_callbacks(execute=True):
        Plain.objects.create(name="Nothing to see here")

    assert transport.count == 0


@override_settings(HTML2IMG={"API_KEY": "test-key", "ON_SAVE": "thread"})
def test_thread_mode_renders_off_the_request_cycle(
    monkeypatch: pytest.MonkeyPatch,
    transport: FakeTransport,
    django_capture_on_commit_callbacks,
) -> None:
    """The work happens in a worker thread, against a freshly loaded object.

    The render itself is stubbed here: a real background thread gets its own
    database connection, which an in-memory test database does not share.
    """
    import threading

    seen: list = []
    main_thread = threading.current_thread().name

    def record(model, pk):
        seen.append((model, pk, threading.current_thread().name))

    monkeypatch.setattr("html2img_django.signals._generate", record)

    with django_capture_on_commit_callbacks(execute=True):
        post = Post.objects.create(title="Threaded")

    for thread in threading.enumerate():
        if thread.name.startswith("html2img-og-"):
            thread.join(timeout=10)

    assert seen and seen[0][0] is Post
    assert seen[0][1] == post.pk
    assert seen[0][2] != main_thread
