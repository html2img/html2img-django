# Publishing `html2img-django` to PyPI

Django packages are published to PyPI exactly like any other Python package —
there is no separate plugin marketplace to submit to, the way Statamic and Craft
have. The listing sites that matter are directories that read PyPI, so getting
the metadata right *is* the marketing work.

If you have not published a Python package before, read
[PUBLISHING.md in html2img-python](https://github.com/html2img/html2img-python/blob/main/PUBLISHING.md)
first. It explains how PyPI differs from Packagist and npm, and covers the
one-time setup that applies to both packages:

- the `html2img` brand account on `pypi@html2img.com`, and why not a personal one
- why a paid PyPI organisation is not worth it yet
- tokens, trusted publishing, and TestPyPI rehearsals
- the handover checklist if html2img ever changes hands

This package is published from that same account. Everything below is what is
specific to it.

## Publish the client first

`html2img-django` depends on `html2img-client>=1.0`. That dependency must exist
on PyPI before this package is installable, so:

1. Publish `html2img-client` from the
   [html2img-python](https://github.com/html2img/html2img-python) repo.
2. Confirm it installs cleanly: `pip install html2img-client`.
3. Then publish this package.

If you publish them the other way round, `pip install html2img-django` fails at
the dependency resolution step for anyone who tries it in the gap.

## The first release needs no API token

A project that does not exist yet can still be published by GitHub Actions,
using a [pending publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
The project is created by the first successful upload, and the pending publisher
becomes a normal one at that moment. This is the route to use — a token is only
needed if you insist on uploading by hand.

At [pypi.org/manage/account/publishing](https://pypi.org/manage/account/publishing/),
under "Add a new pending publisher", enter:

| Field | Value |
| --- | --- |
| PyPI Project Name | `html2img-django` |
| Owner | `html2img` |
| Repository name | `html2img-django` |
| Workflow name | `publish.yml` |
| Environment name | `pypi` |

Then create the `pypi` environment in the GitHub repo under
**Settings → Environments**. No secrets are needed.

One caveat: a pending publisher does not reserve the project name. The name is
only claimed on the first successful upload.

## Release steps

Every release, including the first, is the same three commands:

```bash
# 1. Bump __version__ in src/html2img_django/__init__.py
# 2. Move the Unreleased entries in CHANGELOG.md under the new version, with a date
# 3. Commit, tag, release

git commit -am "Release 1.1.0"
git tag v1.1.0
git push origin main --follow-tags
gh release create v1.1.0 --generate-notes
```

Publishing the GitHub release runs `.github/workflows/publish.yml`, which builds,
runs `twine check`, and uploads over OIDC with no token anywhere. It also
generates [PEP 740 attestations](https://peps.python.org/pep-0740/), so the
release carries verifiable provenance.

To sanity-check the artefacts before tagging:

```bash
rm -rf dist/ && python -m build && twine check dist/*
```

which runs `.github/workflows/publish.yml` and uploads with no token involved.

## Verifying the release end to end

A Django package can pass `twine check` and still be broken, because the real
test is whether it works inside a Django project. Before announcing a release:

```bash
python -m venv /tmp/h2i-django && source /tmp/h2i-django/bin/activate
pip install html2img-django django
django-admin startproject demo && cd demo

# add "html2img_django" to INSTALLED_APPS, then:
HTML2IMG_API_KEY=your-key python manage.py html2img_test
```

`html2img_test` exercises the settings, the registry, the template lookup and a
real render, which is most of the package in one command. The
[html2img-django-test](https://github.com/html2img/html2img-django-test) project
does the same thing with content and an admin already set up.

## Making the package findable

PyPI is the registry, but Django developers mostly discover packages elsewhere.
After the first release:

1. **[Django Packages](https://djangopackages.org/)** — the directory Django
   developers browse. Add the package at
   [djangopackages.org/packages/add/](https://djangopackages.org/packages/add/);
   it pulls metadata from PyPI and GitHub automatically. Add it to the
   "SEO", "Social" and "Images" grids, which is where anyone comparing options
   will look.
2. **Trove classifiers** — `pyproject.toml` already declares
   `Framework :: Django` and the supported versions. These power the "Django"
   filters on PyPI and libraries.io, so keep them current when you add support
   for a new Django release.
3. **The README** is the PyPI project page. It is the highest-authority backlink
   the package produces, so the links in it matter; check they all render on
   `https://pypi.org/project/html2img-django/` after the first upload.
4. **GitHub topics** — add `django`, `django-package`, `open-graph`,
   `og-image`, `social-images`, `html-to-image` to the repository. GitHub topic
   pages are indexed and are a common discovery path.
5. **Awesome lists** — [awesome-django](https://github.com/wsvincent/awesome-django)
   takes pull requests for packages that are documented, tested and released.

## When you add Django or Python support

1. Add the version to the CI matrix in `.github/workflows/ci.yml`.
2. Add the matching trove classifier in `pyproject.toml`.
3. Update the "Requirements" section of the README and the badge.
4. Note it in the changelog. Dropping a version is a major release; adding one
   is a minor release.

## The release checklist

```
[ ] html2img-client is published and installs cleanly
[ ] CI green on main, across the whole Django matrix
[ ] Version bumped in src/html2img_django/__init__.py
[ ] CHANGELOG.md updated with the new version and date
[ ] rm -rf dist/ && python -m build && twine check dist/*
[ ] Installed into a scratch Django project and `html2img_test` passes
[ ] git tag vX.Y.Z && git push --tags
[ ] GitHub release published (this uploads to PyPI)
[ ] Project page renders correctly on pypi.org
[ ] Django Packages entry updated (first release only)
```
