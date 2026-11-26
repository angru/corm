from copy import deepcopy
from typing import Any

from corm import Entity, Field, MissingFieldError, Nested, Storage


class Badge(Entity):
    id: int = Field(pk=True)


class Member(Entity):
    id: int = Field(pk=True)
    badges: list[Badge] = Nested(default=list)
    name: str = Field(origin="display_name", destination="name")


def load_member(payload: dict[str, Any], storage: Storage, *omit: str) -> Member:
    data = {key: deepcopy(value) for key, value in payload.items() if key not in omit}
    return Member(data, storage)


payload = {
    "id": 7,
    "display_name": "Amina",
    "badges": [{"id": 42}],
    "import_batch": "November",
}
original = deepcopy(payload)

store = Storage()
member = load_member(payload, store, "import_batch")
assert member.dict() == {"id": 7, "name": "Amina", "badges": [{"id": 42}]}
assert store.get(Member.id, 7) is member
assert store.get(Badge.id, 42) is member.badges[0]

store = Storage()
member = load_member(payload, store, "import_batch", "badges")
assert member.dict() == {"id": 7, "name": "Amina", "badges": []}
assert store.get(Member.id, 7) is member
assert store.get(Badge.id, 42) is None

for required_key in ("id", "display_name"):
    candidate = Storage()
    try:
        load_member(payload, candidate, required_key)
    except MissingFieldError:
        assert candidate.get(Member.id, 7) is None
    else:
        raise AssertionError(f"Expected a missing field for {required_key}")

    # The primary key loads first. In this model badges load before the name.
    badge = candidate.get(Badge.id, 42)
    if required_key == "id":
        assert badge is None
    else:
        assert isinstance(badge, Badge) and badge.id == 42

assert payload == original
