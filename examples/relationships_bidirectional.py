from corm import Storage, Entity, Relationship, Nested


class Address(Entity):
    street: str
    number: int
    user: 'User' = Relationship(entity_type='User')


class User(Entity):
    name: str
    address: Address = Nested(
        entity_type=Address,
        back_relation=True,
    )


storage = Storage()
john = User(
    data={
        'name': 'John',
        'address': {
            'street': 'First',
            'number': 1,
        },
    },
    storage=storage,
)

assert john.address.user == john
