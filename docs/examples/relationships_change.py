from corm import Entity, Nested, Relationship, Storage


class Address(Entity):
    street: str
    user: "User" = Relationship()


class User(Entity):
    id: int
    address: Address = Nested(back_relation=True)


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

assert old_address.user is john

address = Address(data={"street": "lenina"}, storage=storage)
john.address = address

assert old_address.user is None
assert address.user == john
assert john.address is address
