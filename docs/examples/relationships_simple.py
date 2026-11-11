from corm import Entity, Nested, Storage


class Address(Entity):
    street: str
    number: int


class User(Entity):
    name: str
    address: Address = Nested()


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

assert john.address.street == "First"
assert john.address.number == 1
