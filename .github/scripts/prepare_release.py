import re
import sys
import tomllib
from pathlib import Path


def release_notes(tag: str) -> str:
    with Path("pyproject.toml").open("rb") as project_file:
        version = tomllib.load(project_file)["project"]["version"]
    if tag != f"v{version}":
        raise SystemExit(
            f"Release tag {tag!r} must match v{version} in pyproject.toml."
        )

    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    for section in re.split(r"^## ", changelog, flags=re.MULTILINE)[1:]:
        heading, _, notes = section.partition("\n")
        if heading.strip() == version and notes.strip():
            return notes.strip("\n")

    raise SystemExit(f"CHANGELOG.md must have a nonempty '## {version}' section.")


if __name__ == "__main__":
    print(release_notes(sys.argv[1]))
