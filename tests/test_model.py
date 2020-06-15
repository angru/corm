import typing as t

import pytest

from corm import Model, Field, Storage, Nested, Relationship, NestedKey, RelationType, KeyRelationship


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


def test_relationship():
    class Entity(Model):
        name: str

    class EntityHolder(Model):
        name: str
        entity: Entity = Relationship(entity_type=Entity, relation_type=RelationType.CHILD)

    storage = Storage()
    holder = EntityHolder(data={'name': 'holder'}, storage=storage)
    entity1 = Entity(data={'name': 'entity1'}, storage=storage)

    assert holder.entity is None

    storage.make_relation(from_=holder, to_=entity1, relation_type=RelationType.CHILD)

    assert holder.entity == entity1

    class ManyEntityHolder(Model):
        name: str
        entities: t.List[Entity] = Relationship(entity_type=Entity, many=True, relation_type=RelationType.CHILD)

    holder = ManyEntityHolder(data={'mane': 'many holder'}, storage=storage)
    entity2 = Entity(data={'name': 'entity2'}, storage=storage)

    storage.make_relation(from_=holder, to_=entity1, relation_type=RelationType.CHILD)
    storage.make_relation(from_=holder, to_=entity2, relation_type=RelationType.CHILD)

    assert holder.entities == [entity1, entity2]

    with pytest.raises(ValueError):
        storage.make_relation(from_=holder, to_=entity2, relation_type=RelationType.CHILD)


def test_nested_key():
    class Entity(Model):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Model):
        name: str
        entity: Entity = NestedKey(Entity.id, 'entity_id')

    storage = Storage()
    entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert holder.name is None

    class ManyEntityHolder(Model):
        name: str
        entities: t.List[Entity] = NestedKey(related_entity_field=Entity.id, key='entity_ids', many=True)

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


def test_key_relationship():
    class Entity(Model):
        id: int = Field(pk=True)
        name: str
        holder: 'EntityHolder' = KeyRelationship(
            entity_type='EntityHolder', field_name='id', relation_type=RelationType.CHILD,
        )

    class EntityHolder(Model):
        name: str
        entity: Entity = NestedKey(
            related_entity_field=Entity.id, key='entity_id', back_relation_type=RelationType.CHILD,
        )

    storage = Storage()
    entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert entity.holder == holder



def test_same_pk():
    class User(Model):
        id: int = Field(pk=True)

    storage = Storage()
    User({'id': 1}, storage)

    with pytest.raises(ValueError):
        User({'id': 1}, storage)


def multiple_primary_keys():
    class User(Model):
        id: int = Field(pk=True)
        guid: str = Field(pk=True)
        name: str

    storage = Storage()
    user = User({'id': 1, 'guid': '1234', 'name': 'john'}, storage)

    assert storage.get(User.id, 1) == user
    assert storage.get(User.guid, '1234') == user
    assert storage.get(User.name, 'john') is None


def test_self_related():
    class Item(Model):
        id: int
        items: t.List['Item'] = Nested(entity_type='Item', many=True, back_relation_type=RelationType.CHILD)
        parent: 'Item' = Relationship(entity_type='Item', relation_type=RelationType.CHILD)

    storage = Storage()
    item1 = Item({'id': 1, 'items': [{'id': 2}, {'id': 3}]}, storage)
    item2, item3 = item1.items

    assert item1.id == 1
    assert item1.parent is None

    assert item2.id == 2
    assert item2.parent == item1
    assert item2.items == []

    assert item3.id == 3
    assert item3.parent == item1
    assert item3.items == []
