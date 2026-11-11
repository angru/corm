import pytest
from prepare_release import release_notes


@pytest.fixture
def release_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.0.4"\n')
    return tmp_path


def test_extracts_only_matching_changelog_section(release_checkout):
    (release_checkout / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "## Unreleased\n\nFuture changes\n\n"
        "## 0.0.40\n\nDifferent release\n\n"
        "## 0.0.4\n\n### Fixed\n\n- A bug.\n\n"
        "## 0.0.3\n\nOlder release\n"
    )

    assert release_notes("v0.0.4") == "### Fixed\n\n- A bug."


def test_rejects_a_mismatched_tag_before_reading_changelog(release_checkout):
    with pytest.raises(SystemExit, match=r"Release tag 'v0\.0\.5' must match v0\.0\.4"):
        release_notes("v0.0.5")


@pytest.mark.parametrize("heading", ["## 0.0.40\n\nDifferent release", "## 0.0.4\n\n"])
def test_requires_nonempty_notes_for_the_version(release_checkout, heading):
    (release_checkout / "CHANGELOG.md").write_text(f"# Changelog\n\n{heading}\n")

    with pytest.raises(SystemExit, match=r"nonempty '## 0\.0\.4' section"):
        release_notes("v0.0.4")
