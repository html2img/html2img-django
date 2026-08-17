[![html2img — HTML to image API, rendered in real Chrome](https://html2img.com/og-image.png)](https://html2img.com)

# Open Graph Images for Django

[![PyPI Version](https://img.shields.io/pypi/v/html2img-django)](https://pypi.org/project/html2img-django/)
[![Python Versions](https://img.shields.io/pypi/pyversions/html2img-django)](https://pypi.org/project/html2img-django/)
[![Django Versions](https://img.shields.io/badge/django-4.2%20%7C%205.x%20%7C%206.x-092E20)](https://www.djangoproject.com/)
[![License](https://img.shields.io/pypi/l/html2img-django)](LICENSE)

Automatic Open Graph (social share) images for your Django models, rendered by the [HTML to Image API](https://html2img.com) in real Chrome. You design the card as an ordinary Django template with full CSS control, and the package renders it against each object, sends the HTML to the API, and stores the returned image URL on the model.

Because the design is a template in your project rather than a fixed layout, flexbox, grid, custom properties, web fonts and anything else you can write in CSS behave exactly as they do in the browser. Built on the official [html2img Python client](https://pypi.org/project/html2img-client/).

> ⚠️ **A free html2img API key is required.** This package generates your Open Graph images through the [HTML to Image API](https://html2img.com), so it needs a key to render anything. Creating an account is free and includes 50 credits, with no card needed to get started. Images rendered on the free tier are hosted for seven days; on any paid plan they are hosted permanently, including everything you rendered before upgrading.
>
> **→ [Get your free API key at app.html2img.com](https://app.html2img.com/register)**

## What it does

- Renders a developer-authored Django template into an Open Graph image when an object is saved, off the request cycle, and stores the `i.html2img.com` URL on the model.
- Resolves settings through a cascade: project defaults, then per-model registration options, then per-object overrides.
- Skips the render when the inputs are unchanged, so routine saves spend no credits.
- Outputs the social tags itself, or hands the URL to the SEO package you already use.
- Ships a staff-only live preview, an admin panel, a regenerate action and a bulk management command.

## Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Designing the card](#designing-the-card)
  - [Template context](#template-context)
  - [The preview loop](#the-preview-loop)
  - [Local development and public URLs](#local-development-and-public-urls)
- [Configuration](#configuration)
- [Registering models](#registering-models)
- [Outputting the tags](#outputting-the-tags)
- [When images are generated](#when-images-are-generated)
- [Storage modes](#storage-modes)
- [Bulk regeneration](#bulk-regeneration)
- [The admin](#the-admin)
- [Generating something other than an OG image](#generating-something-other-than-an-og-image)
- [Errors and logging](#errors-and-logging)
- [Verifying your setup](#verifying-your-setup)
- [Testing your project](#testing-your-project)
- [Other integrations](#other-integrations)
- [Development](#development)
- [Links](#links)

## Requirements

- Python 3.10 or newer
- Django 4.2 or newer (4.2 LTS, 5.x, 6.x)
- A free [HTML to Image](https://app.html2img.com/register) API key; every account starts with 50 free credits

## Installation

```bash
pip install html2img-django
```

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "html2img_django",
]
```

Put your API key in the environment. This is the canonical source:

```dotenv
HTML2IMG_API_KEY=your-api-key
```

See the [authentication docs](https://html2img.com/docs/authentication) for issuing and rotating keys.

## Quick start

**1. Add the mixin to a model and migrate.** It contributes the fields the pipeline needs, plus the editor-facing overrides:

```python
from django.db import models
from html2img_django import OpenGraphImageMixin


class Post(OpenGraphImageMixin, models.Model):
    title = models.CharField(max_length=200)
    excerpt = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
```

```bash
python manage.py makemigrations && python manage.py migrate
```

**2. Register the model.** Create an `og_images.py` module in the app. It is imported automatically at startup, the same way `admin.py` is:

```python
# blog/og_images.py
from html2img_django import og_images

from .models import Post

og_images.register(Post)
```

**3. Output the tags** in your base template:

```html+django
{% load og_image %}
<head>
    {% og_image_meta object %}
</head>
```

**4. Add the preview routes** (optional, but it is how you design the card):

```python
# urls.py
urlpatterns = [
    path("og-images/", include("html2img_django.urls")),
]
```

**5. Save a post.** The card renders in the background and the image URL lands on the object. Check it worked:

```bash
python manage.py html2img_test
```

That is the whole setup. Everything below is customisation.

## Designing the card

The bundled default template (`html2img_django/default.html`) is a complete 1200×630 card, and it is deliberately plain so you replace it. Copy it into your project and point the settings at your copy:

```python
HTML2IMG = {
    "TEMPLATE": "og/post.html",
}
```

Or per model, which is the usual case once you have more than one content type:

```python
og_images.register(Post, template="og/post.html")
og_images.register(Product, template="og/product.html", height=800)
```

The template is rendered to a string and posted to the [HTML to Image API](https://html2img.com), so anything a browser can render works: web fonts from a CDN, gradients, `object-fit`, `-webkit-line-clamp` for truncation, SVG, even inline JavaScript.

### Template context

Every card is rendered with:

| Variable       | What it is                                                                 |
| -------------- | -------------------------------------------------------------------------- |
| `object`       | The model instance. Also available under its model name, so a `Post` is `post`. |
| `og_headline`  | The `og_image_headline` override, falling back to `title`, then `str(obj)`. |
| `og_subtitle`  | The `og_image_subtitle` override, if set.                                   |
| `site_name`    | `HTML2IMG["SITE_NAME"]`, or the current `Site` name.                        |
| `site_logo`    | `HTML2IMG["SITE_LOGO"]`, an absolute URL.                                   |

Add your own by overriding `og_image_context()` on the model:

```python
class Post(OpenGraphImageMixin, models.Model):
    def og_image_context(self):
        return {
            "author": self.author.get_full_name(),
            "date": self.published_at,
            "image": self.cover.url if self.cover else "",
        }
```

or with a `context` callable at registration, which keeps the model clean:

```python
og_images.register(
    Post,
    template="og/post.html",
    context=lambda post: {"reading_time": post.reading_time()},
)
```

Guard optional fields with `{% if %}` so a single template can serve several models:

```html+django
{% if author %}<span class="author">{{ author }}</span>{% endif %}
{% if image %}<img src="{{ image }}" alt="">{% endif %}
```

### The preview loop

Design in the browser. The package ships a preview route that renders your template at the exact configured dimensions, with no API key required and no credits spent, because the browser renders the same HTML the API does:

- `/og-images/preview/` — the card with representative sample data.
- `/og-images/preview/blog.Post/1/` — the card for a real object.

Both are staff-only. The admin also embeds the live preview next to the last render, which is the parity check between what you designed and what the API produced.

Once the design looks right, save the object (or use the admin's **Regenerate Open Graph images** action) to render it for real.

### Local development and public URLs

Renders happen on the HTML to Image servers in real Chrome, so every URL in your template — web fonts, images, stylesheets — must be reachable from the public internet. In production your media and static URLs already are, so the rendered image matches the browser preview.

On a local development site this is not the case: an image served from `localhost:8000` or `*.ddev.site` is invisible to the API and shows as missing in the rendered PNG, even though your browser preview shows it. The fix is to reference publicly hosted assets, or to expose your dev site with a tunnel (`cloudflared tunnel --url ...`, `ddev share`, `ngrok http 8000`) and build absolute URLs against it while you test. Web fonts loaded from a public CDN such as Google Fonts always work, because they are already public.

## Configuration

Everything lives in one `HTML2IMG` dict in your settings. Anything you leave out uses the default:

```python
HTML2IMG = {
    "API_KEY": None,  # falls back to $HTML2IMG_API_KEY
    "TEMPLATE": "html2img_django/default.html",
    "WIDTH": 1200,
    "HEIGHT": 630,
    "DPI": 2,
    "FORMAT": "png",
    "STORAGE": "cdn",  # or "media"
    "MEDIA_PATH": "og-images/{app_label}/{model_name}/{pk}.{extension}",
    "SITE_NAME": None,  # falls back to the Sites framework
    "SITE_LOGO": None,
    "DEFAULT_IMAGE": None,  # fallback when an object has no image
    "ON_SAVE": "thread",  # "thread", "sync" or "off"
    "ENABLED": True,
    "TIMEOUT": 35.0,
    "BASE_URL": None,  # only for private deployments
}
```

| Key             | Default                        | Purpose                                                                     |
| --------------- | ------------------------------ | --------------------------------------------------------------------------- |
| `API_KEY`       | `$HTML2IMG_API_KEY`            | Sent as the `X-API-Key` header. Keep it out of version control.             |
| `TEMPLATE`      | the bundled default            | The template rendered into the image.                                       |
| `WIDTH`/`HEIGHT`| `1200` / `630`                 | Image size in CSS pixels. 1200×630 is the standard OG size.                 |
| `DPI`           | `2`                            | Device pixel ratio, 1 to 4. 2 is retina.                                    |
| `FORMAT`        | `"png"`                        | `"png"` or `"pdf"`. See the [HTML to PDF API](https://html2img.com/html-to-pdf/). |
| `STORAGE`       | `"cdn"`                        | `"cdn"` keeps the CDN URL; `"media"` downloads into Django storage.         |
| `MEDIA_PATH`    | see above                      | Path template for `"media"` storage.                                        |
| `SITE_NAME`     | the current `Site`             | Passed to every card template.                                              |
| `SITE_LOGO`     | none                           | Absolute URL of a logo, passed to every card template.                      |
| `DEFAULT_IMAGE` | none                           | Used by the tags when an object has no image of its own.                    |
| `ON_SAVE`       | `"thread"`                     | How a save is handled. See [when images are generated](#when-images-are-generated). |
| `ENABLED`       | `True`                         | Master switch. Set `False` in tests and local development.                  |
| `TIMEOUT`       | `35.0`                         | Request timeout in seconds.                                                 |

An unknown key raises `ImproperlyConfigured` at startup rather than being silently ignored, so a typo shows up immediately.

### A custom API client

All requests go through one client, so you can supply your own — for retry middleware, a proxy, or request logging:

```python
# blog/apps.py
from html2img import Html2img
from html2img_django.client import set_client


class BlogConfig(AppConfig):
    def ready(self):
        set_client(Html2img(transport=my_retrying_transport))
```

See [custom transports](https://github.com/html2img/html2img-python#custom-transports) in the client's README.

## Registering models

`og_images.register()` takes the model and any per-model overrides:

```python
og_images.register(
    Post,
    template="og/post.html",  # the card design
    width=1200,  # image size
    height=630,
    dpi=2,  # 2 for retina
    format="png",  # or "pdf"
    storage="cdn",  # or "media"
    context=lambda post: {...},  # extra template context
    queryset=lambda: Post.objects.filter(published=True),  # what bulk regeneration walks
)
```

It also works as a decorator:

```python
@og_images.register(template="og/product.html")
class Product(OpenGraphImageMixin, models.Model): ...
```

Registrations belong in an `og_images.py` module in any installed app; they are imported for you at startup. Registering a model that does not use `OpenGraphImageMixin` raises `ImproperlyConfigured` with an explanation, rather than failing later at render time.

### Per-object overrides

The mixin gives editors three escape hatches, all optional:

- **`og_image_headline`** and **`og_image_subtitle`** — override the text on the card without touching the title.
- **`og_image_custom`** — an image URL that bypasses generation entirely. Override `get_og_custom_image()` to point it at an uploaded file instead:

  ```python
  def get_og_custom_image(self):
      return self.social_image.url if self.social_image else ""
  ```

- **`og_image_disabled`** — never generate an image for this object.

## Outputting the tags

### Standalone

```html+django
{% load og_image %}

<head>
    <title>{{ object.title }}</title>
    {% og_image_meta object %}
</head>
```

That writes `og:image`, `og:image:width`, `og:image:height`, `og:image:type`, `og:image:alt`, `twitter:card` and `twitter:image`, resolving the cascade (custom image, then generated image, then `DEFAULT_IMAGE`). If there is no image at all, it writes nothing rather than empty tags.

`{% og_image_url object %}` returns just the URL, for feeds, JSON-LD, emails or an `<img>` tag:

```html+django
<meta property="og:image" content="{% og_image_url object %}">
```

### With an existing SEO package

If you already run [django-meta](https://pypi.org/project/django-meta/), [wagtail-metadata](https://pypi.org/project/wagtail-metadata/) or your own meta layer, skip the tags and feed it the URL. `get_og_image_url()` on the model resolves the same cascade:

```python
class Post(OpenGraphImageMixin, models.Model):
    def as_meta(self, request=None):
        meta = super().as_meta(request)
        meta.image = self.get_og_image_url()

        return meta
```

## When images are generated

`HTML2IMG["ON_SAVE"]` decides what a save does. In every mode the work is deferred to `transaction.on_commit`, so nothing renders against a state that then rolls back:

- **`"thread"`** (default) — renders in a background thread, so the save returns immediately. Good for the admin and for small to medium sites; the thread gets its own database connection and closes it when done.
- **`"sync"`** — renders inline. Simple and predictable, but the save waits for the API (up to a few seconds).
- **`"off"`** — nothing happens automatically. Use this when you have a real task queue and want to drive it yourself.

### With Celery, RQ or Huey

For anything busy, set `ON_SAVE` to `"off"` and dispatch from your own task, which gives you retries, rate limiting and visibility:

```python
# blog/tasks.py
from celery import shared_task
from django.apps import apps
from html2img_django import generate


@shared_task(bind=True, max_retries=3)
def generate_og_image(self, label: str, pk: int) -> None:
    model = apps.get_model(label)
    obj = model.objects.filter(pk=pk).first()

    if obj is not None:
        generate(obj)
```

```python
# blog/signals.py
@receiver(post_save, sender=Post)
def queue_og_image(sender, instance, **kwargs):
    transaction.on_commit(lambda: generate_og_image.delay(sender._meta.label, instance.pk))
```

`generate(obj, force=False)` is the single entry point: it resolves the settings, renders the card, calls the API and stores the result. It returns the stored URL, or `None` when nothing was rendered.

When you need to know *what* happened — whether a credit was actually spent — use `generate_result()`, which returns the same work with a verdict attached:

```python
from html2img_django import generate_result

result = generate_result(post)

result.url  # str | None
result.rendered  # True only when the API was called and returned an image
result.reused  # True when the card was unchanged, so nothing was rendered
result.ok  # True when the object ended up with an image, either way
result.reason  # "unchanged", "opted-out", "disabled", "error", "no-url", "unsaved"
```

## Storage modes

- **`"cdn"`** (default) — stores the `i.html2img.com` URL on the object. Nothing to serve, and the CDN handles the traffic. Images render permanently on paid plans.
- **`"media"`** — downloads the render into your Django storage (`default_storage`, so S3 and friends work through [django-storages](https://django-storages.readthedocs.io/)) and stores that URL instead. Use it when you would rather not depend on a third-party URL in your markup.

```python
HTML2IMG = {
    "STORAGE": "media",
    "MEDIA_PATH": "social/{app_label}/{model_name}/{pk}.{extension}",
}
```

If the download or the write fails, the CDN URL is kept, so a storage problem never loses a render.

## Bulk regeneration

After changing a card template, regenerate across your registered models:

```bash
python manage.py generate_og_images
python manage.py generate_og_images --model blog.Post --force
python manage.py generate_og_images --dry-run
python manage.py generate_og_images --model blog.Post --limit 50
```

- `--force` ignores the input fingerprint and re-renders everything (this spends a credit per object).
- Without `--force`, objects whose card has not changed are reported as unchanged and cost nothing.
- `--dry-run` lists what would be rendered without calling the API.

The summary line separates the two, so you always know what a run cost:

```
blog.Post: 3 object(s)
  How real Chrome rendering changes social images: https://i.html2img.com/abc123.png
  Designing a card that survives a very long title: unchanged, kept https://i.html2img.com/def456.png
  Why the fingerprint matters: skipped (opted out or has a custom image)
Done. 1 rendered, 1 unchanged, 1 skipped, 0 failed.
```

## The admin

Mix `OpenGraphImageAdminMixin` into a `ModelAdmin` for a live preview, the last render, and a regenerate action:

```python
from django.contrib import admin
from html2img_django.admin import OpenGraphImageAdminMixin

from .models import Post


@admin.register(Post)
class PostAdmin(OpenGraphImageAdminMixin, admin.ModelAdmin):
    list_display = ("title", "published_at", "og_image_status")
    readonly_fields = ("og_image_preview",)
```

`og_image_status` reports whether an object has a generated image, a custom one, or opted out. The preview panel needs the package's URLs to be included.

## Generating something other than an OG image

The package is deliberately focused on Open Graph images, but the same account and key drive the whole API through the [Python client](https://pypi.org/project/html2img-client/), which is installed as a dependency:

```python
from html2img import Html2img

client = Html2img()

# A screenshot of a live URL — https://html2img.com/screenshot-api/
client.screenshot("https://example.com/pricing", fullpage=True, dpi=2)

# An invoice as a vector PDF — https://html2img.com/html-to-pdf/
client.html(render_to_string("invoices/show.html", {"invoice": invoice}), format="pdf")

# A ready-made template, no markup of your own — https://html2img.com/templates
client.template("invoice-image", {"number": 1042, "amount": "£240.00"})
```

Screenshots are a natural fit for link previews, article thumbnails and monitoring; PDFs for invoices, tickets and reports, where text stays selectable and long content paginates automatically.

## Errors and logging

Nothing in the pipeline raises into your request cycle. A failed render is logged and the object keeps whatever image it had, so a hiccup at the API never breaks a save or a page. Everything is logged under the `html2img_django` logger:

```python
LOGGING = {
    "version": 1,
    "loggers": {
        "html2img_django": {"handlers": ["console"], "level": "INFO"},
    },
}
```

At `DEBUG` you also see why an object was skipped (unchanged inputs, opted out, custom image, rendering disabled). The messages carry the API's `code` and HTTP status, which map to the [documented error codes](https://html2img.com/docs/getting-started/#error-responses).

## Verifying your setup

```bash
python manage.py html2img_test
```

It prints the resolved settings, the registered models, whether your card template can be found, and then renders a small test image and reports your remaining credits. The render uses one credit; pass `--no-render` to check the configuration without spending one.

## Testing your project

Switch rendering off so your test suite never calls the API:

```python
# settings/test.py
HTML2IMG = {"ENABLED": False}
```

With `ENABLED` set to `False`, saves do nothing and `generate()` returns `None`. When you do want to assert on the pipeline, inject a client backed by a fake transport:

```python
from html2img import Html2img
from html2img_django.client import set_client, reset_client


def fake_transport(*, method, url, headers, body, timeout):
    return 200, b'{"success": true, "url": "https://i.html2img.com/test.png"}'


set_client(Html2img("test-key", transport=fake_transport))
# ... exercise your code ...
reset_client()
```

## Other integrations

The same API has official packages and worked guides for
[Python](https://github.com/html2img/html2img-python),
[Laravel](https://html2img.com/integrations/laravel/),
[PHP](https://html2img.com/integrations/php/),
[Statamic](https://html2img.com/integrations/statamic/),
[WordPress](https://html2img.com/integrations/wordpress/),
[JavaScript and Node.js](https://html2img.com/integrations/javascript/),
[React](https://html2img.com/integrations/javascript/#react-and-nextjs),
[Vue](https://html2img.com/integrations/javascript/#vue-and-nuxt) and
[Ruby and Rails](https://html2img.com/integrations/ruby/).

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

pytest              # tests, no network and no credits spent
ruff check .        # lint
ruff format .       # format
mypy                # static analysis
```

A ready-made Django project for exercising the package by hand lives in
[html2img-django-test](https://github.com/html2img/html2img-django-test). Publishing to PyPI is covered in [PUBLISHING.md](PUBLISHING.md).

## Links

[HTML to Image API](https://html2img.com) · [Screenshot API](https://html2img.com/screenshot-api/) · [HTML to PDF API](https://html2img.com/html-to-pdf/) · [Documentation](https://html2img.com/docs) · [Templates](https://html2img.com/templates) · [Tools](https://html2img.com/tools) · [Features](https://html2img.com/features) · [Pricing](https://html2img.com/pricing) · [Python client](https://github.com/html2img/html2img-python)

## Licence

MIT. See [LICENSE](LICENSE).
