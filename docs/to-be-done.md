## Entity settings class

```python
from corm import Storage, Entity



class Address(Entity):
    class Config:
        exclude = ('description',)

    street: str
    number: int


storage = Storage()
address = Address(
    data={'street': 'Second', 'number': 2, 'description': 'address'},
    storage=storage,
)

assert address.dict() == {'street': 'Second', 'number': 2}
```


## Change data through relationships

```python
import typing as t

from corm import Storage, Entity, Nested



class Address(Entity):
    street: str
    number: int

class User(Entity):
    name: str
    addresses: t.List[Address] = Nested(entity_type=Address, many=True)


storage = Storage()
john = User(
    data={
        'name': 'John',
        'addresses': [{'street': 'First', 'number': 1}]
    },
    storage=storage,
)
additional_address = Address(
    data={'street': 'Second', 'number': 2}, storage=storage,
)

john.addresses.append(additional_address)

assert john.dict() == {
    'name': 'John',
    'addresses': [
        {'street': 'First', 'number': 1},
        {'street': 'Second', 'number': 2},
    ],
}
```

## Entity migration between different instances of storage

```python
from corm import Storage, Entity, Field


class User(Entity):
    id: int = Field(pk=True)

storage1 = Storage()
storage2 = Storage()
user = User(data={'id': 1}, storage=storage1)

storage2.merge(user)

assert storage1.get(User.id, 1) is None
assert storage2.get(User.id, 1) is user
```

## Query API

```python
from corm import Storage, Entity

class User(Entity):
    name: str

storage = Storage()
john = User(data={'name': 'John'}, storage=storage)
user = storage.select(User).filter(User.name == 'John').first()

assert user == john
```
