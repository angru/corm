from corm import Storage, Entity, Relationship, RelationType

storage = Storage()


class Address(Entity):
    street: str
    number: int


class User(Entity):
    name: str
    address: Address = Relationship(
        entity_type=Address,
        relation_type=RelationType.PARENT,
    )


address = Address({"street": "First", "number": 1}, storage)
john = User({"name": "John"}, storage)

storage.make_relation(
    from_=john,
    to_=address,
    relation_type=RelationType.PARENT,
)

assert john.address == address
