# Changelog

All notable changes to corm are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

### Changed

- Require Python 3.11 or newer and test on Python 3.11 through 3.15. Use uv,
  Ruff, and pre-commit for development.
  ([#28](https://github.com/angru/corm/pull/28))
- Expose `AccessMode` as a combinable `IntFlag`.
  ([#34](https://github.com/angru/corm/pull/34))

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
