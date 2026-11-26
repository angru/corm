import pytest

from corm import Entity, Field, KeyManager, KeyNested, Storage


class ExistingKeyManager(KeyManager):
    def get(self, record):
        return record["id"]

    def prepare_to_set(self, entity):
        return {"id": entity.id}


def test_default_manager_rewrites_plain_key():
    class Target(Entity):
        id: int = Field(pk=True)

    manager = KeyNested(Target.id).key_manager
    assert manager.get(manager.rewrite_key(1, 5)) == 5


def test_existing_manager_can_read_and_write_without_implementing_rewrite():
    class Target(Entity):
        id: int = Field(pk=True)

    manager = ExistingKeyManager()

    class Owner(Entity):
        target = KeyNested(Target.id, key_manager=manager)

    storage = Storage()
    before = Target({"id": 1}, storage)
    after = Target({"id": 5}, storage)
    owner = Owner({"target": {"id": 1}}, storage)
    assert owner.target is before
    owner.target = after
    assert owner.target is after
    assert owner.dict() == {"target": {"id": 5}}
    with pytest.raises(NotImplementedError, match="does not support rewriting"):
        manager.rewrite_key({"id": 1}, 5)
