from corm import Entity, Field, KeyNested, Storage


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str


class EntityHolder(Entity):
    name: str
    entities: list[SomeEntity] = KeyNested(
        related_entity_field=SomeEntity.id,
        origin="entity_ids",
    )


storage = Storage()
entity = SomeEntity({"id": 123, "name": "entity"}, storage=storage)
holder = EntityHolder({"entity_ids": [123], "name": "holder"}, storage=storage)

assert holder.entities == [entity]
