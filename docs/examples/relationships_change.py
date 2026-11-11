from corm import Entity, Nested, Relationship, Storage


class Address(Entity):
    street: str
    user: "User | None" = Relationship()


class User(Entity):
    id: int
    address: Address | None = Nested(back_populates="user")


storage = Storage()
john = User(
    data={
        "id": 1,
        "name": "John",
        "description": "john smith",
        "address": {
            "street": "kirova",
        },
    },
    storage=storage,
)

old_address = john.address

assert old_address is not None
assert old_address.user is john

address = Address(data={"street": "lenina"}, storage=storage)
john.address = address

assert old_address.user is None
assert address.user is john
assert john.address is address

jane = User({"id": 2, "address": {"street": "First"}}, storage)
displaced = jane.address
assert displaced is not None
address.user = jane

assert john.address is None
assert jane.address is address
assert address.user is jane
assert displaced.user is None

address.user = None
assert jane.address is None
assert address.user is None
