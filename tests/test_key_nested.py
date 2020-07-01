import typing as t

import pytest

from corm import Entity, Field, KeyNested, Storage, Relationship, KeyManager


def test_nested_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_id',
        )

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert holder.dict() == {'entity_id': 123}

    class ManyEntityHolder(Entity):
        entities: t.List[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_ids',
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
        holder: 'EntityHolder' = Relationship('EntityHolder')

    class EntityHolder(Entity):
        entities: t.List[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_ids',
            many=True,
            back_relation=True,
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


def test_complex_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityKeyManager(KeyManager):
        def get(self, data):
            return data['id']

        def prepare_to_set(self, entity: SomeEntity) -> t.Any:
            return {'id': entity.id}

    class ManyEntityHolder(Entity):
        entities: t.List[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_ids',
            many=True,
            key_manager=EntityKeyManager(),
        )

    storage = Storage()
    entity1 = SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
    entity2 = SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder(
        {
            'entity_ids': [
                {
                    'id': 123,
                },
                {
                    'id': 321,
                },
            ],
        },
        storage=storage,
    )

    assert holder.entities == [entity1, entity2]
    assert holder.dict() == {'entity_ids': [{'id': 123}, {'id': 321}]}


def test_change_values():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str
        holder: 'EntityHolder' = Relationship(entity_type='EntityHolder')
        many_holder: 'ManyEntityHolder' = Relationship(
            entity_type='ManyEntityHolder',
        )

    class EntityKeyManager(KeyManager):
        def get(self, data):
            return data['id']

        def prepare_to_set(self, entity: SomeEntity) -> t.Any:
            return {'id': entity.id}

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_id',
            key_manager=EntityKeyManager(),
            back_relation=True,
        )

    class ManyEntityHolder(Entity):
        entities: t.List[SomeEntity] = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_ids',
            many=True,
            back_relation=True,
            key_manager=EntityKeyManager(),
        )

    storage = Storage()
    entity1 = SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
    entity2 = SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = EntityHolder(
        {
            'entity_id': {
                'id': 123,
            },
        },
        storage=storage,
    )

    holder.entity = entity2

    assert entity1.holder is None
    assert entity2.holder is holder
    assert holder.entity is entity2
    assert holder.dict() == {'entity_id': {'id': 321}}

    many_holder = ManyEntityHolder(
        {
            'entity_ids': [{
                'id': 123,
            }],
        },
        storage=storage,
    )

    many_holder.entities = [entity2]

    assert many_holder.entities == [entity2]
    assert entity1.many_holder is None
    assert entity2.many_holder is many_holder
    assert many_holder.dict() == {
        'entity_ids': [{
            'id': 321,
        }],
    }


@pytest.mark.skip(reason='Not implemented yet')
def test_change_key_value():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(Entity):
        entity: SomeEntity = KeyNested(
            related_entity_field=SomeEntity.id,
            origin='entity_id',
        )

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    entity.id = 321

    assert holder.entity == entity
    assert holder.dict() == {'entity_id': 321}
