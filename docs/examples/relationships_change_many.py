from corm import Entity, Nested, Relationship, Storage


class Address(Entity):
    street: str
    users: list["User"] = Relationship()


class User(Entity):
    id: int
    addresses: list[Address] = Nested(back_populates="users", default=list)


storage = Storage()
john = User(
    data={
        "id": 1,
        "name": "John",
        "description": "john smith",
        "addresses": [
            {
                "street": "kirova 1",
            },
            {
                "street": "kirova 2",
            },
        ],
    },
    storage=storage,
)

old_address1, old_address2 = john.addresses

# you can change existing list
john.addresses.remove(old_address1)

assert old_address1.users == []
assert old_address2.users == [john]

john.addresses.clear()

assert old_address1.users == []
assert old_address2.users == []
assert john.addresses == []

new_address1 = Address(data={"street": "lenina 1"}, storage=storage)
new_address2 = Address(data={"street": "lenina 2"}, storage=storage)

john.addresses.append(new_address1)

assert new_address1.users == [john]
assert john.addresses == [new_address1]

john.addresses.extend([new_address2])

assert new_address2.users == [john]
assert john.addresses == [new_address1, new_address2]

# or completely replace it
john.addresses = [old_address1]

assert new_address1.users == []
assert new_address2.users == []
assert old_address1.users == [john]

jane = User({"id": 2}, storage)
old_address1.users.append(jane)
assert jane.addresses == [old_address1]

old_address1.users.remove(john)
assert john.addresses == []

old_address1.users = [john]
assert jane.addresses == []
assert john.addresses == [old_address1]
