"""Prototype for the fixed Directory schema, with one independently owned store."""

from copy import deepcopy
from typing import cast

from corm import DuplicateKeyError, KeyNested, RelationError, Storage
from docs.examples.storage_renumber_user import Directory, Group, User


def rekey(directory: Directory, user: User, new_id: int) -> None:
    store = directory.storage
    old_id = user.id
    if store.get(User.id, old_id) is not user or user not in directory.users:
        raise ValueError("Expected a user from this directory")
    if old_id == new_id:
        return
    if store.get(User.id, new_id) is not None:
        raise DuplicateKeyError(f"User ID {new_id} is occupied")

    # Capture the reverse order while the old key still resolves. Prepare every
    # replacement before writing, including conflicts in the last group.
    changes = []
    for group in user.groups:
        members = group.dict()["members"]
        if any(item["user_id"] == new_id for item in members):
            raise RelationError(f"Group already references user ID {new_id}")
        changes.append(
            (
                group,
                [
                    {**item, "user_id": new_id} if item["user_id"] == old_id else item
                    for item in members
                ],
            )
        )

    update_lead = directory.lead is user
    user.id = new_id
    if update_lead:
        directory.lead = user
    # The public list setter accepts entities and regenerates raw membership
    # records. The prototype needs the internal writer to retain ranks and keys.
    field = cast(KeyNested, Group.members)
    for group, records in changes:
        field._replace_paired_data(group, records)


def check():
    store = Storage()
    directory = Directory(
        {
            "users": [{"id": 1}, {"id": 2}],
            "lead_id": 1,
            "groups": [
                {"members": [{"user_id": 1, "rank": 3}]},
                {"members": [{"user_id": 9, "rank": 1}, {"user_id": 1, "rank": 2}]},
            ],
        },
        store,
    )
    user, other = directory.users
    first, last = directory.groups
    before = deepcopy(directory.dict())
    for new_id, error in [(2, DuplicateKeyError), (9, RelationError)]:
        try:
            rekey(directory, user, new_id)
        except error:
            pass
        else:
            raise AssertionError(f"Expected a conflict for {new_id}")
        assert directory.dict() == before
        assert store.get(User.id, 1) is directory.lead is user
        assert store.get(User.id, 2) is other and store.get(User.id, 9) is None
        assert first.members == last.members == [user]
        assert user.groups == [first, last] and other.groups == []

    rekey(directory, user, 5)
    rekey(directory, user, 5)
    assert store.get(User.id, 1) is None
    assert store.get(User.id, 5) is directory.lead is user
    assert directory.users[0] is user and user.groups == [first, last]
    assert first.members == last.members == [user]
    assert directory.dict() == {
        **before,
        "users": [{"id": 5}, {"id": 2}],
        "lead_id": 5,
        "groups": [
            {"members": [{"user_id": 5, "rank": 3}]},
            {"members": [{"user_id": 9, "rank": 1}, {"user_id": 5, "rank": 2}]},
        ],
    }
    late = User({"id": 9}, store)
    assert last.members == [late, user] and late.groups == [last]
    replacement = User({"id": 1}, store)
    assert replacement.groups == []


if __name__ == "__main__":
    check()
