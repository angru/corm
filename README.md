# corm

<!-- --8<-- [start:overview] -->
corm wraps nested dictionaries from parsed JSON or YAML in lightweight Python
entities. If you've ever needed to get the parent of a nested model, corm gives
the child a back-reference to its parent. It also resolves ID references through
an in-memory identity map. corm wraps the input dictionaries in place without
copying or validating them. Undeclared keys are preserved, and `dict()` exports
the data as dictionaries again.

## Example

A project API returns users and sprints. Each sprint embeds its tasks, and each
task stores an `assignee_id`. The example follows both links, moves a task to a
new sprint, and checks that the export preserves the task's assignee and
undeclared keys such as `labels`.
<!-- --8<-- [end:overview] -->

<!-- BEGIN PROJECT EXAMPLE -->

```python
from corm import Entity, Field, KeyNested, Nested, Relationship, Storage


class User(Entity):
    id: int = Field(pk=True)
    name: str
    tasks: list["Task"] = Relationship()


class Task(Entity):
    title: str
    assignee: User = KeyNested(User.id, origin="assignee_id", back_populates="tasks")
    sprint: "Sprint | None" = Relationship()


class Sprint(Entity):
    name: str
    tasks: list[Task] = Nested(back_populates="sprint")


class Project(Entity):
    name: str
    users: list[User] = Nested()
    sprints: list[Sprint] = Nested()


payload = {
    "name": "Customer portal",
    "archived": False,
    "users": [{"id": 42, "name": "Amina", "timezone": "UTC"}],
    "sprints": [
        {
            "name": "Sprint 12",
            "tasks": [
                {
                    "title": "Add invoice download",
                    "assignee_id": 42,
                    "labels": ["billing"],
                }
            ],
        },
        {"name": "Sprint 13", "tasks": []},
    ],
}

project = Project(payload, Storage())
current_sprint, next_sprint = project.sprints
(task,) = current_sprint.tasks
(user,) = project.users

assert project.name == "Customer portal"
assert task.title == "Add invoice download"
assert task.sprint is current_sprint
assert task.assignee is user
assert user.tasks == [task]

task.sprint = next_sprint

assert current_sprint.tasks == []
assert next_sprint.tasks == [task]
assert task.sprint is next_sprint
assert task.assignee is user
assert user.tasks == [task]

assert project.dict() == {
    "name": "Customer portal",
    "archived": False,
    "users": [{"id": 42, "name": "Amina", "timezone": "UTC"}],
    "sprints": [
        {"name": "Sprint 12", "tasks": []},
        {
            "name": "Sprint 13",
            "tasks": [
                {
                    "title": "Add invoice download",
                    "assignee_id": 42,
                    "labels": ["billing"],
                }
            ],
        },
    ],
}
```

<!-- END PROJECT EXAMPLE -->

[Read the runnable project example](docs/examples/project.py). From the checkout,
run it with `uv run python docs/examples/project.py`.

## When to use corm

<!-- --8<-- [start:comparison] -->
Use corm to edit a document in memory when your code often navigates from a child
to its parent or follows references by ID. corm is not a validation library and
is not optimized for speed. Choose a validation or decoding library for untrusted
input, a dot-access wrapper for simple attribute access, or SQLite with an ORM
when you need queries, joins, or transactions.

| Tool | Validation | Back-references | References by ID | Preserves unknown keys | Typed attribute access |
| --- | --- | --- | --- | --- | --- |
| corm | No | Built in with `back_populates` | Built in with `KeyNested` | Yes, by default | Yes, for declared fields |
| [Pydantic](https://docs.pydantic.dev/latest/api/config/#pydantic.config.ConfigDict.extra) | Yes | Application code | Application code | With `extra="allow"` | Yes |
| [attrs](https://www.attrs.org/) + [cattrs](https://catt.rs/) / [msgspec](https://msgspec.dev/structs) | attrs validators / typed decoding in msgspec | Application code | Application code | Requires explicit handling | Yes |
| [python-box](https://github.com/cdgriffith/Box) | No | Application code | Application code | Yes, as mapping keys | Dynamic dot access |
| In-memory SQLite + [ORM](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html) | Database constraints | With mapped relationships | With foreign keys and joins | Explicit storage, such as a JSON column | With typed ORM models |
<!-- --8<-- [end:comparison] -->

## Installation

<!-- --8<-- [start:installation] -->
Install with `pip install corm`. corm is in early development, and its API may
change.
<!-- --8<-- [end:installation] -->

See the [documentation](https://angru.github.io/corm/) and [changelog](CHANGELOG.md).

## Development

Install the `docs`, `lint`, and `test` dependency groups with
[uv](https://github.com/astral-sh/uv) using `uv sync --locked --all-groups`.
Run `uv run pre-commit run --all-files` for lint and formatting checks,
`uv run pytest` for tests, and `uv run mkdocs build --strict` to build the docs.

After editing `docs/examples/project.py`, refresh the README example with
`uv run python .github/scripts/sync_readme_example.py`.

### Documentation deployment

The docs workflow publishes changes from `master` to `gh-pages` and requests
a GitHub Pages build. It uses the built-in Actions token. In GitHub Pages
settings, the publishing source is **Deploy from a branch** with `gh-pages`
and `/ (root)`. See the
[GitHub Pages publishing settings](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).

## Building

Run `uv build` to create a wheel and source distribution under `dist/`.

## Releasing

Before the first release, create the `pypi` environment in the GitHub settings
for `angru/corm` and allow release tags to deploy automatically. In the PyPI
`corm` project's Publishing settings, add a GitHub trusted publisher with owner
`angru`, repository `corm`, workflow `release.yml`, and environment `pypi`. The
workflow authenticates to PyPI with OIDC. See the
[PyPI setup guide](https://docs.pypi.org/trusted-publishers/adding-a-publisher/).

1. Bump the version in `pyproject.toml` and refresh `uv.lock` with `uv lock`.
2. Add a nonempty `## <version>` section to [CHANGELOG.md](CHANGELOG.md).
3. Once the release changes are on `master`, tag the release commit and push
   that tag. For version 0.0.4, run `git tag -a v0.0.4 -m "Release 0.0.4"` and
   `git push origin v0.0.4`.

GitHub Actions checks the version, runs the tests, builds and publishes both
distributions to PyPI, and creates a GitHub Release with the matching changelog
section and both distributions attached.
