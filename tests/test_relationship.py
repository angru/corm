import typing as t

import pytest

from corm import Entity, Relationship, RelationType, Storage


def test_relationship():
    class SomeEntity(Entity):
        name: str

    class EntityHolder(Entity):
        name: str
        entity: SomeEntity = Relationship(
            entity_type=SomeEntity,
            relation_type=RelationType.CHILD,
        )

    storage = Storage()
    holder = EntityHolder(data={'name': 'holder'}, storage=storage)
    entity1 = SomeEntity(data={'name': 'entity1'}, storage=storage)

    assert holder.entity is None

    storage.make_relation(
        from_=holder,
        to_=entity1,
        relation_type=RelationType.CHILD,
    )

    assert holder.entity == entity1

    class ManyEntityHolder(Entity):
        name: str
        entities: t.List[SomeEntity] = Relationship(
            entity_type=SomeEntity,
            many=True,
            relation_type=RelationType.CHILD,
        )

    holder = ManyEntityHolder(data={'name': 'many holder'}, storage=storage)
    entity2 = SomeEntity(data={'name': 'entity2'}, storage=storage)

    storage.make_relation(
        from_=holder,
        to_=entity1,
        relation_type=RelationType.CHILD,
    )
    storage.make_relation(
        from_=holder,
        to_=entity2,
        relation_type=RelationType.CHILD,
    )

    assert holder.entities == [entity1, entity2]

    with pytest.raises(ValueError):
        storage.make_relation(
            from_=holder,
            to_=entity2,
            relation_type=RelationType.CHILD,
        )
