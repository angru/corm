"""Prototype for the fixed Directory schema, with one independently owned store."""

from copy import deepcopy
from typing import cast

from corm import DuplicateKeyError, Entity, KeyNested, Nested, RelationError, Storage
from docs.examples.storage_renumber_user import Directory, Group, MemberKey, User
from experiments.reference_discovery import unpaired_references


def rewrite_record(manager, record, new_id):
    rewritten = manager.rewrite_key(deepcopy(record), new_id)
    if manager.get(deepcopy(rewritten)) != new_id:
        raise ValueError("Rewritten reference has the wrong key")
    return rewritten


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
    field = cast(KeyNested, Group.members)
    manager = cast(MemberKey, field.key_manager)
    changes = []
    for group in user.groups:
        records = list(group._data["members"])
        for index, record in enumerate(records):
            key = manager.get(deepcopy(record))
            if key == new_id:
                raise RelationError(f"Group already references user ID {new_id}")
            if key == old_id:
                records[index] = rewrite_record(manager, record, new_id)
        changes.append((group, records))

    unpaired = {}
    for owner, relation, index in unpaired_references(directory, User.id, old_id):
        if relation.back_relation:
            raise RelationError("Legacy reverse indexes need a separate update plan")
        origin = relation.origin
        slot = (id(owner), origin)
        if slot not in unpaired:
            raw = owner._data[origin]
            unpaired[slot] = (owner, origin, list(raw) if relation.many else raw)
        _, _, prepared = unpaired[slot]
        if index is None:
            value = rewrite_record(relation.key_manager, prepared, new_id)
            unpaired[slot] = (owner, origin, value)
        else:
            prepared[index] = rewrite_record(
                relation.key_manager, prepared[index], new_id
            )

    old_source = field._key_source(old_id)
    new_source = field._key_source(new_id)
    # For this paired many-to-many schema each changed group moves one edge.
    # Commit the prepared records without calling the key manager again.
    user.id = new_id
    for owner, origin, value in unpaired.values():
        owner._data[origin] = value
    for group, records in changes:
        store.remove_relation(old_source, group, field)
        store.make_relation(new_source, group, field)
        group._data["members"] = records
        field._mark_list_changed(group)


def check():
    store = Storage()
    directory = Directory(
        {
            "users": [{"id": 1}, {"id": 2}],
            "lead_id": 1,
            "groups": [
                {
                    "members": [
                        {"user_id": 1, "rank": 3, "labels": {"names": ["review"]}}
                    ]
                },
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
            {"members": [{"user_id": 5, "rank": 3, "labels": {"names": ["review"]}}]},
            {"members": [{"user_id": 9, "rank": 1}, {"user_id": 5, "rank": 2}]},
        ],
    }
    late = User({"id": 9}, store)
    assert last.members == [late, user] and late.groups == [last]
    replacement = User({"id": 1}, store)
    assert replacement.groups == []


def check_nested_document():
    class ReviewKey(MemberKey):
        reject_rank = 2

        def rewrite_key(self, record, new_key):
            if record["rank"] == self.reject_rank:
                record["labels"].clear()
                raise ValueError("Rejected final reviewer")
            return super().rewrite_key(record, new_key)

    manager = ReviewKey()

    class Review(Entity):
        reviewers = KeyNested(
            User.id,
            origin="reviewer_ids",
            many=True,
            key_manager=manager,
            required=False,
        )

    class ReviewDirectory(Directory):
        reviews: list[Review] = Nested()

    reviewers = [
        {"user_id": key, "rank": rank, "labels": ["keep"]}
        for rank, key in enumerate([1, 9, 1])
    ]
    store = Storage()
    directory = ReviewDirectory(
        {
            "users": [{"id": 1}],
            "lead_id": 1,
            "groups": [{"members": [{"user_id": 1, "rank": 4}]}],
            "reviews": [
                {"reviewer_ids": reviewers},
                {"reviewer_ids": [deepcopy(reviewers[0])]},
            ],
        },
        store,
    )
    user = directory.lead
    before = deepcopy(directory.dict())
    try:
        rekey(directory, user, 5)
    except ValueError as error:
        assert str(error) == "Rejected final reviewer"
    else:
        raise AssertionError("Expected the reviewer rewrite to fail")
    assert directory.dict() == before
    assert directory.lead is store.get(User.id, 1) is user
    assert store.get(User.id, 5) is None
    assert user.groups == directory.groups and directory.groups[0].members == [user]

    manager.reject_rank = -1
    rekey(directory, user, 5)
    expected = deepcopy(before)
    expected["users"][0]["id"] = expected["lead_id"] = 5
    expected["groups"][0]["members"][0]["user_id"] = 5
    for review in expected["reviews"]:
        for record in review["reviewer_ids"]:
            if record["user_id"] == 1:
                record["user_id"] = 5
    assert directory.dict() == expected
    assert directory.lead is store.get(User.id, 5) is user
    assert store.get(User.id, 1) is None
    assert user.groups == directory.groups and directory.groups[0].members == [user]
    first, second = directory.reviews
    assert first.reviewers == [user, user] and second.reviewers == [user]
    late = User({"id": 9}, store)
    assert first.reviewers == [user, late, user]


if __name__ == "__main__":
    check()
    check_nested_document()
