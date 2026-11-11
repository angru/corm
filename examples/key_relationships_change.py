from corm import Entity, Field, KeyNested, Relationship, Storage


class SomeEntity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: "EntityHolder | None" = Relationship()


class EntityHolder(Entity):
    entity: SomeEntity | None = KeyNested(
        related_entity_field=SomeEntity.id,
        origin="entity_id",
        back_populates="holder",
    )


storage = Storage()
entity1 = SomeEntity({"id": 123, "name": "entity1"}, storage=storage)
entity2 = SomeEntity({"id": 321, "name": "entity2"}, storage=storage)
holder = EntityHolder(
    data={"entity_id": 123},
    storage=storage,
)

holder.entity = entity2

assert entity1.holder is None
assert entity2.holder is holder
assert holder.entity is entity2
assert holder.dict() == {"entity_id": 321}

new_holder = EntityHolder({"entity_id": None}, storage)
entity2.holder = new_holder

assert holder.entity is None
assert holder.dict() == {"entity_id": None}
assert new_holder.entity is entity2
assert new_holder.dict() == {"entity_id": 321}
