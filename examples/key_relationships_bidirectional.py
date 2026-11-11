from corm import (
    Entity,
    Field,
    KeyNested,
    Relationship,
    Storage,
)


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: "EntityHolder | None" = Relationship()


class EntityHolder(Entity):
    name: str
    entity: SomeEntity = KeyNested(
        related_entity_field=SomeEntity.id,
        origin="entity_id",
        back_populates="holder",
    )


storage = Storage()
holder = EntityHolder({"name": "holder", "entity_id": 123}, storage=storage)
entity = SomeEntity({"id": 123, "name": "entity"}, storage=storage)

assert holder.entity == entity
assert entity.holder == holder
