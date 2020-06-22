import typing as t

import pytest

from corm import Entity, Field, NestedKey, Storage


def test_nested_key():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str

    class EntityHolder(SomeEntity):
        entity: SomeEntity = NestedKey(SomeEntity.id, 'entity_id')

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'entity_id': 123}, storage=storage)

    assert holder.entity == entity

    class ManyEntityHolder(SomeEntity):
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

    storage = Storage()
    SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
    SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
    holder = ManyEntityHolder({'entity_ids': [123, 99999]}, storage=storage)

    with pytest.raises(ValueError):
        holder.entities
