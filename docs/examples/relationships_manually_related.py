from corm import Entity, Relationship, RelationType, Storage

storage = Storage()


class Address(Entity):
    street: str
    number: int


class User(Entity):
    name: str
    address: Address | None = Relationship(relation_type=RelationType.PARENT)


address = Address({"street": "First", "number": 1}, storage)
john = User({"name": "John"}, storage)

storage.make_relation(
    from_=john,
    to_=address,
    relation_type=RelationType.PARENT,
)

assert john.address == address

storage.remove_relation(
    from_=john,
    to_=address,
    relation_type=RelationType.PARENT,
)

assert john.address is None
