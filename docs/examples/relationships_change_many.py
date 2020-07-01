import typing as t

from corm import Entity, Relationship, Nested, Storage


class Address(Entity):
    street: str
    user: 'User' = Relationship(entity_type='User')


class User(Entity):
    id: int
    addresses: t.List[Address] = Nested(
        entity_type=Address,
        back_relation=True,
        many=True,
    )


storage = Storage()
john = User(
    data={
        'id': 1,
        'name': 'John',
        'description': 'john smith',
        'addresses': [
            {
                'street': 'kirova 1',
            },
            {
                'street': 'kirova 2',
            },
        ],
    },
    storage=storage,
)

old_address1, old_address2 = john.addresses

# you can change existing list
john.addresses.remove(old_address1)

assert old_address1.user is None
assert old_address2.user is john

john.addresses.clear()

assert old_address1.user is None
assert old_address2.user is None
assert john.addresses == []

new_address1 = Address(data={'street': 'lenina 1'}, storage=storage)
new_address2 = Address(data={'street': 'lenina 2'}, storage=storage)

john.addresses.append(new_address1)

assert new_address1.user is john
assert john.addresses == [new_address1]

john.addresses.extend([new_address2])

assert new_address2.user is john
assert john.addresses == [new_address1, new_address2]

# or completely replace it
john.addresses = [old_address1]

assert new_address1.user is None
assert new_address2.user is None
assert old_address1.user is john
