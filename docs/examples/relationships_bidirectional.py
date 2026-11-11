from corm import Entity, Nested, Relationship, Storage


class Address(Entity):
    street: str
    number: int
    user: "User | None" = Relationship()


class User(Entity):
    name: str
    address: Address | None = Nested(back_populates="user")


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
