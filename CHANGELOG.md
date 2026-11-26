# Changelog

All notable changes to corm are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## Unreleased

## 0.0.5

### Added

- Omit top-level output keys with `entity.dict(exclude=["id"])`.
  ([#7](https://github.com/angru/corm/issues/7))
- Add runnable recipes for request-scoped storage, copying and renumbering a
  document, and transforming input and output with FastAPI or cattrs.

### Changed

- Allocate paired-list revision counters on the first edit. On CPython 3.14.5,
  retained Python allocations fell by 13.9% in the read benchmark and 2.2% in
  the benchmark that removes and restores each link.
  ([#65](https://github.com/angru/corm/pull/65))

## 0.0.4

### Added

- Pair a `Nested` or `KeyNested` field with a reverse `Relationship` using
  `back_populates`. Editing either side updates both fields.
  ([#33](https://github.com/angru/corm/pull/33))
- Infer the related entity type and whether it is a list from annotations.
  ([#32](https://github.com/angru/corm/pull/32))
- Ship a `py.typed` marker and expose a `CormError` hierarchy for library errors.
  ([#34](https://github.com/angru/corm/pull/34))
- Automate PyPI publishing and GitHub Releases from version tags.
  ([#29](https://github.com/angru/corm/pull/29))
- Add runnable documentation examples and benchmarks for document setup and
  traversal. ([#35](https://github.com/angru/corm/pull/35),
  [#36](https://github.com/angru/corm/pull/36))

### Changed

- Require Python 3.11 or newer and test on Python 3.11 through 3.15. Use uv,
  Ruff, and pre-commit for development.
  ([#28](https://github.com/angru/corm/pull/28))
- Expose `AccessMode` as a combinable `IntFlag`.
  ([#34](https://github.com/angru/corm/pull/34))
- Update paired list relationships incrementally on append and remove.
  Repeated `owner.targets.append(item)` calls can reuse unretained list views
  on GIL-enabled CPython. Previously retained views and dictionary exports
  keep their contents. ([#42](https://github.com/angru/corm/pull/42))

### Deprecated

- Use `back_populates` for new reverse links. The `back_relation` argument
  remains available and emits a deprecation warning.
  ([#33](https://github.com/angru/corm/pull/33))

### Removed

- Remove the unused `corm.hooks` module.
  ([#27](https://github.com/angru/corm/pull/27))

### Fixed

- Preserve nested entity data when exporting dictionaries. Fix field inference
  and relationship reassignment, and reject duplicate keys before loading
  relationships for the duplicate entity.
  ([#27](https://github.com/angru/corm/pull/27))
- Resolve relationships to instances of subclasses of the declared type.
  ([#30](https://github.com/angru/corm/pull/30))
- Keep primary-key lookup in sync with key changes and keep relation reads
  from changing the index. Index relation membership while preserving order.
  ([#31](https://github.com/angru/corm/pull/31))
- Preserve raw input keys that share a name with a `Relationship` field
  when exporting an entity with `dict()`. ([#40](https://github.com/angru/corm/pull/40))
- Allow a redefined owner class to take over its `back_populates` pair.
  Instances of the previous class are stale after the handoff.
  ([#41](https://github.com/angru/corm/pull/41))
