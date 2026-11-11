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

# Rationale

* сложно помнить ключи словарей, если структура данных большая
* организация двусторонних связей между сущностями, особенно иерархических структурах данных
* возможность разделить безнес-логику и технические детали связывания сущностей друг с другом и поиска связанной сущности
