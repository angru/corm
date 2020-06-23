import typing as t

import pytest

from corm import Entity, Field, NestedKey, Storage, Relationship, RelationType


def test_nested_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Entity):
        entity: SomeEntity = NestedKey(
            related_entity_field=SomeEntity.id,
            key='entity_id',
        )

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert holder.dict() == {'entity_id': 123}

    class ManyEntityHolder(Entity):
        entities: t.List[SomeEntity] = NestedKey(
            related_entity_field=SomeEntity.id,
            key='entity_ids',
            many=True,
        )

    storage = Storage()
    entity1 = SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
    entity2 = SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder({'entity_ids': [123, 321]}, storage=storage)

    assert holder.entities == [entity1, entity2]
    assert holder.dict() == {'entity_ids': [123, 321]}

    storage = Storage()
    SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
    SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder({'entity_ids': [123, 99999]}, storage=storage)

    with pytest.raises(ValueError):
        holder.entities


def test_make_back_relationship():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str
        holder: 'EntityHolder' = Relationship(
            'EntityHolder',
            relation_type=RelationType.RELATED,
        )

    class EntityHolder(Entity):
        entities: t.List[SomeEntity] = NestedKey(
            related_entity_field=SomeEntity.id,
            key='entity_ids',
            many=True,
            back_relation_type=RelationType.RELATED,
        )

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_ids': [123, 456]}, storage=storage)
    delayed_entity = SomeEntity(
        {
            'id': 456,
            'name': 'delayed entity',
        },
        storage=storage,
    )

    assert holder.entities == [entity, delayed_entity]
    assert entity.holder == holder
    assert delayed_entity.holder == holder

    assert holder.dict({'entity_ids': [123, 456]})
    assert entity.dict() == {'id': 123, 'name': 'entity'}
    assert delayed_entity.dict() == {'id': 456, 'name': 'delayed entity'}
