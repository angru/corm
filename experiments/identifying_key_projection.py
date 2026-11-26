"""Compare response projection with removing a referenced key before loading.

Run with: python -m experiments.identifying_key_projection
"""

from copy import deepcopy
from typing import Any

from corm import (
    Entity,
    Field,
    KeyNested,
    MissingFieldError,
    Nested,
    Relationship,
    Storage,
)


class User(Entity):
    id: int = Field(pk=True)
    name: str
    tasks: list["Task"] = Relationship()


class Task(Entity):
    id: int = Field(pk=True)
    assignee: User = KeyNested(User.id, origin="assignee_id", back_populates="tasks")


class Project(Entity):
    # Load the referencing task before its target to exercise pending references.
    tasks: list[Task] = Nested()
    users: list[User] = Nested()


def load(data: dict[str, Any], store: Storage) -> Project:
    return Project(deepcopy(data), store)


payload = {
    "tasks": [{"id": 10, "assignee_id": 7}],
    "users": [{"id": 7, "name": "Amina"}],
}
original = deepcopy(payload)
store = Storage()
project = load(payload, store)
task, user = project.tasks[0], project.users[0]
assert store.get(Task.id, 10) is task
assert store.get(User.id, 7) is user
assert task.assignee is user and user.tasks == [task]

# exclude applies to output keys at this entity's top level, not recursively.
response = project.dict()
response["users"] = [user.dict(exclude={"id"}) for user in project.users]
assert response == {
    "tasks": [{"id": 10, "assignee_id": 7}],
    "users": [{"name": "Amina"}],
}
assert project.dict() == original
assert store.get(User.id, 7) is user and task.assignee is user
assert user.tasks == [task]

# The full export reloads into a fresh store with the same internal identities.
reloaded_store = Storage()
reloaded = load(project.dict(), reloaded_store)
assert reloaded_store.get(Task.id, 10) is reloaded.tasks[0]
assert reloaded_store.get(User.id, 7) is reloaded.users[0]
assert reloaded.tasks[0].assignee is reloaded.users[0]
assert reloaded.users[0].tasks == [reloaded.tasks[0]]

# Both a projected response and an input with the key removed lack the required ID.
for candidate in (response, {"tasks": payload["tasks"], "users": [{"name": "Amina"}]}):
    failed_store = Storage()
    try:
        load(candidate, failed_store)
    except MissingFieldError as exc:
        assert "id" in str(exc) and "User" in str(exc)
    else:
        raise AssertionError("Expected the referenced user's missing ID to fail")
    assert failed_store.get(User.id, 7) is None
    orphan = failed_store.get(Task.id, 10)
    assert isinstance(orphan, Task)
    # The pending incoming reference also remains in the supplied store.
    replacement = User({"id": 7, "name": "Later"}, failed_store)
    assert orphan.assignee is replacement and replacement.tasks == [orphan]

assert payload == original
