import argparse
from pathlib import Path

START = "<!-- BEGIN PROJECT EXAMPLE -->\n"
END = "<!-- END PROJECT EXAMPLE -->\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Synchronize the README example.")
    parser.add_argument("--check", action="store_true", help="Check without writing.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    readme = root / "README.md"
    example = root / "docs/examples/project.py"
    original = readme.read_text(encoding="utf-8")

    before, start, rest = original.partition(START)
    _, end, after = rest.partition(END)
    if not start or not end or original.count(START) != 1 or original.count(END) != 1:
        raise SystemExit("README.md must have one pair of project example markers.")

    code = example.read_text(encoding="utf-8").rstrip("\n")
    rendered = f"{before}{start}\n```python\n{code}\n```\n\n{end}{after}"
    if rendered == original:
        return
    if args.check:
        raise SystemExit(
            "README.md example is out of sync. Run "
            "uv run python .github/scripts/sync_readme_example.py."
        )
    readme.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
