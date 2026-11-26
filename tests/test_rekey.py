from copy import deepcopy

import pytest

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


class MemberKey(KeyManager):
    def get(self, data):
        return data["user_id"]

    def rewrite_key(self, record, new_key):
        record["user_id"] = new_key
        return record

    def prepare_to_set(self, entity):
        return {"user_id": entity.id}


class RekeyUser(Entity):
    id = Field(pk=True)
    groups: list["RekeyGroup"] = Relationship(many=True)
    owner: "RekeyGroup | None" = Relationship(many=False)


class RekeyGroup(Entity):
    members: list[RekeyUser] = KeyNested(
        RekeyUser.id,
        many=True,
        back_populates="groups",
        key_manager=MemberKey(),
        required=False,
    )
    lead: RekeyUser | None = KeyNested(
        RekeyUser.id, back_populates="owner", required=False
    )
    refs = KeyNested(RekeyUser.id, many=True, key_manager=MemberKey(), required=False)
    single = KeyNested(RekeyUser.id, required=False)
    empty = KeyNested(RekeyUser.id, required=False)


class RekeyDocument(Entity):
    users = Nested(RekeyUser, many=True)
    groups = Nested(RekeyGroup, many=True)


def document():
    from corm import registry

    for cls in (RekeyUser, RekeyGroup, RekeyDocument):
        registry.add(cls)
    storage = Storage()
    root = RekeyDocument(
        {
            "users": [{"id": 1}, {"id": 2}],
            "groups": [
                {
                    "members": [{"user_id": 1, "rank": 4}, {"user_id": 9, "rank": 5}],
                    "lead": 1,
                    "refs": [
                        {"user_id": 1, "rank": 6},
                        {"user_id": 9, "rank": 7},
                        {"user_id": 1, "rank": 8},
                    ],
                    "single": 1,
                    "empty": None,
                }
            ],
        },
        storage,
    )
    return storage, root, root.users[0], root.groups[0]


def test_rekey_document_and_pending():
    storage, root, user, group = document()
    storage.rekey(root, user, RekeyUser.id, 5)
    assert storage.get(RekeyUser.id, 1) is None
    assert storage.get(RekeyUser.id, 5) is root.users[0] is user
    assert group.lead is group.single is user
    assert list(group.members) == [user]
    assert group.refs == [user, user]
    assert user.groups == [group] and user.owner is group
    data = root.dict()["groups"][0]
    assert data["members"] == [{"user_id": 5, "rank": 4}, {"user_id": 9, "rank": 5}]
    assert [r["user_id"] for r in data["refs"]] == [5, 9, 5]
    late = RekeyUser({"id": 9}, storage)
    assert list(group.members) == [user, late]
    assert group.refs == [user, late, user]


@pytest.mark.parametrize("key,error", [(2, DuplicateKeyError), (9, RelationError)])
def test_conflicts_leave_state_unchanged(key, error):
    storage, root, user, group = document()
    before = deepcopy(root.dict())
    with pytest.raises(error):
        storage.rekey(root, user, RekeyUser.id, key)
    assert root.dict() == before
    assert storage.get(RekeyUser.id, 1) is user
    assert group.lead is user and list(group.members) == [user]
    assert user.groups == [group] and user.owner is group


def test_late_callback_failure_is_detached(monkeypatch):
    storage, root, user, group = document()
    manager = RekeyGroup.refs.key_manager
    original = manager.rewrite_key

    def fail(record, key):
        record["rank"] = -1
        raise ValueError("late")

    monkeypatch.setattr(manager, "rewrite_key", fail)
    before = deepcopy(root.dict())
    with pytest.raises(ValueError, match="late"):
        storage.rekey(root, user, RekeyUser.id, 5)
    assert root.dict() == before
    assert storage.get(RekeyUser.id, 1) is user and storage.get(RekeyUser.id, 5) is None
    assert list(group.members) == [user] and user.groups == [group]
    monkeypatch.setattr(manager, "rewrite_key", original)


def test_external_paired_owner_rejected():
    storage, root, user, group = document()
    external = RekeyGroup(
        {
            "members": [{"user_id": 1, "rank": 1}],
            "lead": None,
            "refs": [],
            "single": None,
            "empty": None,
        },
        storage,
    )
    before = deepcopy(root.dict())
    with pytest.raises(RelationError, match="outside"):
        storage.rekey(root, user, RekeyUser.id, 5)
    assert root.dict() == before and storage.get(RekeyUser.id, 1) is user
    assert list(external.members) == [user] and list(group.members) == [user]


def test_exclusive_pending_conflict_leaves_indexes_unchanged():
    storage, root, user, group = document()
    pending_owner = RekeyGroup(
        {"members": [], "lead": 5, "refs": [], "single": None, "empty": None},
        storage,
    )
    before = deepcopy(root.dict())
    with pytest.raises(RelationError):
        storage.rekey(root, user, RekeyUser.id, 5)
    assert root.dict() == before
    assert storage.get(RekeyUser.id, 1) is user
    assert storage.get(RekeyUser.id, 5) is None
    assert group.lead is user and user.owner is group
    late = RekeyUser({"id": 5}, storage)
    assert pending_owner.lead is late and late.owner is pending_owner


def test_incompatible_pending_target_rejected_without_writes():
    class Base(Entity):
        id = Field(pk=True)

    class Target(Base):
        owner: "Owner | None" = Relationship()

    class Sibling(Base):
        pass

    class Owner(Entity):
        target: Target | None = KeyNested(
            Target.id, back_populates="owner", required=False
        )

    class Root(Entity):
        target = Nested(Sibling)
        owner = Nested(Owner)

    store = Storage()
    root = Root({"target": {"id": 1}, "owner": {"target": 5}}, store)
    before = deepcopy(root.dict())
    with pytest.raises(RelationError, match="Expected Target"):
        store.rekey(root, root.target, Base.id, 5)
    assert root.dict() == before
    assert store.get(Base.id, 1) is root.target and store.get(Base.id, 5) is None
    assert root.owner.target is None
    late = Target({"id": 5}, store)
    assert root.owner.target is late and late.owner is root.owner
