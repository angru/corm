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


def test_assign_new_value_to_relationship():
    class SomeEntity(Entity):
        name: str

    class EntityHolder(Entity):
        name: str
        entity: SomeEntity = Relationship(entity_type=SomeEntity)

    class ManyEntityHolder(Entity):
        name: str
        entities: t.List[SomeEntity] = Relationship(
            entity_type=SomeEntity,
            many=True,
        )

    storage = Storage()
    holder = EntityHolder(data={'name': 'holder'}, storage=storage)
    entity1 = SomeEntity(data={'name': 'entity1'}, storage=storage)
    entity2 = SomeEntity(data={'name': 'entity2'}, storage=storage)

    holder.entity = entity1

    assert holder.entity is entity1
    assert storage.get_related_entities(
        holder,
        SomeEntity,
        RelationType.RELATED,
    ) == [entity1]

    holder.entity = entity2

    assert holder.entity is entity2
    assert storage.get_related_entities(
        holder,
        SomeEntity,
        RelationType.RELATED,
    ) == [entity2]

    holder.entity = None

    assert holder.entity is None
    assert storage.get_related_entities(
        holder,
        SomeEntity,
        RelationType.RELATED,
    ) == []

    many_holder = ManyEntityHolder(
        data={'name': 'many holder'},
        storage=storage,
    )
    many_holder.entities = [entity1, entity2]

    assert many_holder.entities == [entity1, entity2]
    assert storage.get_related_entities(
        many_holder,
        SomeEntity,
        RelationType.RELATED,
    ) == [entity1, entity2]

    many_holder.entities = []

    assert many_holder.entities == []
    assert storage.get_related_entities(
        many_holder,
        SomeEntity,
        RelationType.RELATED,
    ) == []
