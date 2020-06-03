import typing as t

import pytest

from corm import Model, Field, Storage, Nested, Relationship, KeyRelationship, constants, registry


@pytest.fixture(autouse=True)
def clear_registry():
    registry.clear()


def test_base_model():
    storage = Storage()

    class User(Model):
        id: int
        name: str = Field(default='Bob')

    john = User(
        data={'id': 1, 'name': 'John', 'description': 'john smith'},
        storage=storage,
    )

    assert john.id == 1
    assert john.name == 'John'
    assert john.dict(strip_none=True) == {'id': 1, 'name': 'John', 'description': 'john smith'}


def test_nested():
    storage = Storage()

    class Address(Model):
        street: str

    class User(Model):
        id: int
        name: str = Field(default='Bob')
        address: Address = Nested(entity_type=Address)

    john = User(
        data={'id': 1, 'name': 'John', 'description': 'john smith', 'address': {'street': 'kirova'}},
        storage=storage,
    )

    assert john.address.street == 'kirova'


def test_key_relationship():
    class Entity(Model):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Model):
        name: str
        entity: Entity = KeyRelationship(Entity.id, 'entity_id')

    storage = Storage()
    entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert holder.name is None

    class ManyEntityHolder(Model):
        name: str
        entities: t.List[Entity] = KeyRelationship(related_entity_field=Entity.id, key='entity_ids', many=True)

    storage = Storage()
    entity1 = Entity({'id': 123, 'name': 'entity1'}, storage=storage)
    entity2 = Entity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder({'entity_ids': [123, 321]}, storage=storage)

    assert holder.entities == [entity1, entity2]

    storage = Storage()
    Entity({'id': 123, 'name': 'entity1'}, storage=storage)
    Entity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder({'entity_ids': [123, 99999]}, storage=storage)

    with pytest.raises(ValueError):
        holder.entities
