from corm import Relationship, Entity, Field, KeyNested, Storage


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: 'EntityHolder' = Relationship(entity_type='EntityHolder')


class EntityHolder(Entity):
    entity: SomeEntity = KeyNested(
        related_entity_field=SomeEntity.id,
        origin='entity_id',
        back_relation=True,
    )


storage = Storage()
entity1 = SomeEntity({'id': 123, 'name': 'entity1'}, storage=storage)
entity2 = SomeEntity({'id': 321, 'name': 'entity2'}, storage=storage)
holder = EntityHolder(
    data={'entity_id': 123},
    storage=storage,
)

holder.entity = entity2

assert entity1.holder is None
assert entity2.holder is holder
assert holder.entity is entity2
assert holder.dict() == {'entity_id': 321}
