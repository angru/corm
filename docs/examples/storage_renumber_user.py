from copy import deepcopy

from corm import (
    DuplicateKeyError,
    Entity,
    Field,
    KeyManager,
    KeyNested,
    Nested,
    RelationError,
    Relationship,
    Storage,
)


class User(Entity):
    id: int = Field(pk=True)
    groups: list["Group"] = Relationship()


class MemberKey(KeyManager):
    def get(self, data):
        return data["user_id"]

    def prepare_to_set(self, entity):
        return {"user_id": entity.id}


class Group(Entity):
    members: list[User] = KeyNested(
        User.id, key_manager=MemberKey(), required=False, back_populates="groups"
    )


class Directory(Entity):
    users: list[User] = Nested()
    lead: User = KeyNested(User.id, origin="lead_id")
    groups: list[Group] = Nested()


# --8<-- [start:migration]
def renumber_user(directory: Directory, old_id: int, new_id: int) -> Directory:
    data = deepcopy(directory.dict())
    users = {user["id"]: user for user in data["users"]}
    users[old_id]["id"] = new_id
    if data["lead_id"] == old_id:
        data["lead_id"] = new_id
    for group in data["groups"]:
        for member in group["members"]:
            if member["user_id"] == old_id:
                member["user_id"] = new_id

    candidate = Directory(data, Storage())
    # Loading allows forward references. Resolve the required lead before handoff.
    if candidate.lead is None:
        raise ValueError("The directory needs a lead")
    return candidate


# --8<-- [end:migration]


if __name__ == "__main__":
    source = Directory(
        {
            "users": [{"id": 1}, {"id": 2}],
            "lead_id": 1,
            "groups": [
                {"members": [{"user_id": 9, "rank": 1}, {"user_id": 1, "rank": 2}]}
            ],
        },
        Storage(),
    )
    before = deepcopy(source.dict())
    original = source.lead
    changed = renumber_user(source, 1, 5)
    assert changed.storage.get(User.id, 1) is None
    assert changed.storage.get(User.id, 5) is changed.lead
    assert changed.lead is not original
    assert changed.lead.groups == changed.groups
    assert changed.groups[0].members == [changed.lead]
    assert changed.dict()["groups"][0]["members"] == [
        {"user_id": 9, "rank": 1},
        {"user_id": 5, "rank": 2},
    ]
    late_user = User({"id": 9}, changed.storage)
    assert changed.groups[0].members == [late_user, changed.lead]

    for conflicting_id, error in [(2, DuplicateKeyError), (9, RelationError)]:
        try:
            renumber_user(source, 1, conflicting_id)
        except error:
            pass
        else:
            raise AssertionError(f"Expected a conflict for {conflicting_id}")

    assert source.dict() == before
    assert source.storage.get(User.id, 1) is original
    assert source.storage.get(User.id, 2) is source.users[1]
    assert source.storage.get(User.id, 5) is source.storage.get(User.id, 9) is None
    assert source.lead is original and source.groups[0].members == [original]
    assert original.groups == source.groups
