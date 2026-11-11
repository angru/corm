from corm import Entity, Nested, Relationship, Storage


class Address(Entity):
    street: str
    number: int
    user: "User" = Relationship()


class User(Entity):
    name: str
    address: Address = Nested(back_relation=True)


storage = Storage()
john = User(
    data={
        "name": "John",
        "address": {
            "street": "First",
            "number": 1,
        },
    },
    storage=storage,
)

assert john.address.user == john
