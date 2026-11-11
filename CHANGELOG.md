# Changelog

## 0.0.4

- Require Python 3.11 or newer and test through Python 3.15.
- Fix field inference from annotations and preserve nested entities when
  exporting entity data to dictionaries.
- Fix relationship reassignment and prevent failed entity loads and duplicate
  keys from leaving partial changes in storage.
- Remove the unused `corm.hooks` module.
- Use `uv` for development and packaging, with Ruff and pre-commit for linting
  and formatting.
- Automate PyPI publishing and GitHub Releases from version tags.
