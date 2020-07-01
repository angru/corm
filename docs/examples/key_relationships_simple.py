from corm import Storage, Entity, KeyNested, Field


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str


class EntityHolder(Entity):
    name: str
    entity: SomeEntity = KeyNested(
        related_entity_field=SomeEntity.id,
        origin='entity_id',
    )


storage = Storage()
entity = SomeEntity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'entity_id': 123}, storage=storage)

assert holder.entity == entity
