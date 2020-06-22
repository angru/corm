from corm import Entity, Field, KeyRelationship, RelationType, NestedKey, Storage


def test_key_relationship():
    class SomeEntity(Entity):
        id: int = Field(pk=True)
        name: str
        holder: 'EntityHolder' = KeyRelationship(
            entity_type='EntityHolder',
            field_name='id',
            relation_type=RelationType.CHILD,
        )

    class EntityHolder(Entity):
        name: str
        entity: SomeEntity = NestedKey(
            related_entity_field=SomeEntity.id,
            key='entity_id',
            back_relation_type=RelationType.CHILD,
        )

    storage = Storage()
    entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
    holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

    assert holder.entity == entity
    assert entity.holder == holder
