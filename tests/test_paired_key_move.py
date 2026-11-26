from copy import deepcopy

import pytest

from corm import (
    Entity,
    Field,
    KeyManager,
    KeyNested,
    RelationError,
    Relationship,
    Storage,
)
from corm._rekey import _prepare_paired_key_move


class RecordKey(KeyManager):
    def get(self, record):
        return record["id"]

    def rewrite_key(self, record, key):
        record["id"] = key
        return record


def schema(owner_many, reverse_many):
    class Target(Entity):
        id = Field(pk=True)
        owners = Relationship("Owner", many=reverse_many)

    class Owner(Entity):
        refs = KeyNested(
            Target.id,
            many=owner_many,
            required=False,
            key_manager=RecordKey(),
            back_populates="owners",
        )

    return Target, Owner


@pytest.mark.parametrize("owner_many", [False, True])
@pytest.mark.parametrize("reverse_many", [False, True])
def test_move_paired_keys(owner_many, reverse_many):
    Target, Owner = schema(owner_many, reverse_many)
    store = Storage()
    target = Target({"id": 1}, store)
    record = {"id": 1, "extra": {"keep": [1]}}
    raw = [{"id": 9}, record] if owner_many else record
    owner = Owner({"refs": raw}, store)
    owners = [owner]
    if reverse_many:
        owners.append(Owner({"refs": [{"id": 1}] if owner_many else {"id": 1}}, store))
    pending = None
    if reverse_many:
        pending = Owner({"refs": [{"id": 5}] if owner_many else {"id": 5}}, store)
    plan = _prepare_paired_key_move(Owner.refs, target, 1, 5)
    assert target.id == 1 and owner._data["refs"] == raw
    target.id = 5
    plan.commit()
    assert store.get(Target.id, 5) is target
    assert (list(target.owners) if reverse_many else [target.owners]) == (
        ([pending] if pending else []) + owners
    )
    assert owner._data["refs"] == (
        [{"id": 9}, {"id": 5, "extra": {"keep": [1]}}]
        if owner_many
        else {"id": 5, "extra": {"keep": [1]}}
    )
    if owner_many:
        late = Target({"id": 9}, store)
        assert list(owner.refs) == [late, target]
    else:
        assert owner.refs is target


@pytest.mark.parametrize("owner_many", [False, True])
def test_exclusive_pending_collision_is_rejected_without_writes(owner_many):
    Target, Owner = schema(owner_many, False)
    store = Storage()
    target = Target({"id": 1}, store)
    owner = Owner({"refs": [{"id": 1}] if owner_many else {"id": 1}}, store)
    pending = Owner({"refs": [{"id": 5}] if owner_many else {"id": 5}}, store)
    before = deepcopy([owner._data, pending._data])
    with pytest.raises(RelationError, match="Destination already"):
        _prepare_paired_key_move(Owner.refs, target, 1, 5)
    assert [owner._data, pending._data] == before
    assert store.get(Target.id, 1) is target and store.get(Target.id, 5) is None
    assert target.owners is owner
    late = Target({"id": 5}, store)
    assert late.owners is pending


def test_same_owner_pending_destination_rejected():
    Target, Owner = schema(True, True)
    store = Storage()
    target = Target({"id": 1}, store)
    owner = Owner({"refs": [{"id": 1}, {"id": 5}]}, store)
    before = deepcopy(owner._data)
    with pytest.raises(RelationError, match="destination"):
        _prepare_paired_key_move(Owner.refs, target, 1, 5)
    assert owner._data == before and target.owners == [owner]


def test_commit_does_not_call_manager(monkeypatch):
    Target, Owner = schema(True, True)
    store = Storage()
    target = Target({"id": 1}, store)
    owner = Owner({"refs": [{"id": 1}]}, store)
    plan = _prepare_paired_key_move(Owner.refs, target, 1, 5)

    def fail(*args):
        raise AssertionError("manager called during commit")

    monkeypatch.setattr(Owner.refs.key_manager, "get", fail)
    monkeypatch.setattr(Owner.refs.key_manager, "rewrite_key", fail)
    target.id = 5
    plan.commit()
    assert owner._data["refs"] == [{"id": 5}]
    assert list(target.owners) == [owner]


def test_unpaired_key_field_is_unsupported():
    class Target(Entity):
        id = Field(pk=True)

    class Owner(Entity):
        ref = KeyNested(Target.id)

    store = Storage()
    target = Target({"id": 1}, store)
    with pytest.raises(RelationError, match="paired KeyNested"):
        _prepare_paired_key_move(Owner.ref, target, 1, 5)
    assert store.get(Target.id, 1) is target


def test_null_scalar_record_is_rejected_before_index_move():
    class Target(Entity):
        id = Field(pk=True)
        owners = Relationship("Owner", many=True)

    class Owner(Entity):
        ref = KeyNested(Target.id, back_populates="owners")

    store = Storage()
    target = Target({"id": 1}, store)
    owner = Owner({"ref": 1}, store)
    with pytest.raises(RelationError, match="non-null key"):
        _prepare_paired_key_move(Owner.ref, target, 1, None)
    assert owner.ref is target and target.owners == [owner]
    assert owner.dict() == {"ref": 1}
    assert store.get(Target.id, 1) is target and store.get(Target.id, None) is None
