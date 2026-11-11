# corm

_Data structures relationships made easy_

corm is in early development. API can change.


[![build](https://github.com/angru/corm/workflows/build/badge.svg)](https://github.com/angru/corm/actions?query=workflow%3Abuild+branch%3Amaster++)
[![codecov](https://codecov.io/gh/angru/corm/branch/master/graph/badge.svg)](https://codecov.io/gh/angru/corm)

## Help

See [documentation](https://angru.github.io/corm/) for more details.

## Installation

`pip install corm`

## Development

Install the `docs`, `lint`, and `test` dependency groups using [uv](https://github.com/astral-sh/uv).
```bash
uv venv --python 3.11
uv sync --locked --all-groups
```

Run `uv run pre-commit run --all-files` for lint and formatting checks,
`uv run pytest` for tests, and `uv run mkdocs build --strict` to build the docs.

## Building

To create distribution archives run:
```bash
uv build
```

This produces wheel and source packages under `dist/`.

## Releasing

Before the first release, create the `pypi` environment in the GitHub settings
for `angru/corm` and allow release tags to deploy automatically. In the PyPI
`corm` project's Publishing settings, add a GitHub trusted publisher with owner
`angru`, repository `corm`, workflow `release.yml`, and environment `pypi`. The
workflow authenticates to PyPI with OIDC. See the [PyPI setup guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

1. Bump the version in `pyproject.toml` and refresh `uv.lock` with `uv lock`.
2. Add a nonempty `## <version>` section to [CHANGELOG.md](CHANGELOG.md).
3. Once the release changes are on `master`, tag the release commit and push
   that tag. For the first release, the version is already set to `0.0.4`.

   ```bash
   git tag -a v0.0.4 -m "Release 0.0.4"
   git push origin v0.0.4
   ```

GitHub Actions checks the version, runs the tests, builds the wheel and source
distribution, and publishes both to PyPI. It then creates a GitHub Release with
the matching changelog section and attaches both distributions.

# Rationale

* сложно помнить ключи словарей, если структура данных большая
* организация двусторонних связей между сущностями, особенно иерархических структурах данных
* возможность разделить безнес-логику и технические детали связывания сущностей друг с другом и поиска связанной сущности
