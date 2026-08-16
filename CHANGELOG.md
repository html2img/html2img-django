# Changelog

All notable changes to `html2img-django` are documented here. This project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html) and the
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [Unreleased]

## [1.0.0] - 2026-08-16

Initial release. Automatic Open Graph images for Django, rendered by the
[HTML to Image API](https://html2img.com).

### Added

- `OpenGraphImageMixin`, an abstract model contributing the generated URL, its
  input fingerprint, and the per-object headline, subtitle, custom image and
  opt-out overrides.
- An `og_images` registry with per-model options (template, dimensions, dpi,
  format, storage, extra context, queryset), auto-discovered from each app's
  `og_images.py` module.
- A generation pipeline that renders a Django template, posts it to the API and
  stores the result, skipping the render when the inputs are unchanged.
- `generate()` for the URL, and `generate_result()` when you need to know
  whether a credit was actually spent.
- A `post_save` hook deferred to `transaction.on_commit`, running in a
  background thread, inline, or not at all (`HTML2IMG["ON_SAVE"]`).
- `{% og_image_meta %}` and `{% og_image_url %}` template tags.
- Staff-only preview views for a sample card and for any registered object.
- `OpenGraphImageAdminMixin`: a status column, a live preview panel and a
  regenerate action.
- `generate_og_images` and `html2img_test` management commands.
- `cdn` and `media` storage modes, the latter writing into Django's storage.
- A bundled default card template, ready to copy and customise.

[Unreleased]: https://github.com/html2img/html2img-django/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/html2img/html2img-django/releases/tag/v1.0.0
