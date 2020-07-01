from corm import (
    Storage,
    Field,
    Entity,
    KeyNested,
    Relationship,
)


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: 'EntityHolder' = Relationship(entity_type='EntityHolder')


class EntityHolder(Entity):
    name: str
    entity: SomeEntity = KeyNested(
        related_entity_field=SomeEntity.id,
        origin='entity_id',
        back_relation=True,
    )


storage = Storage()
entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

assert holder.entity == entity
assert entity.holder == holder
