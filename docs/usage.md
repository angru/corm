## Base usage

You can describe wrappers for data structures with `Entity`

```python
from corm import Storage, Entity


class User(Entity):
    id: int
    name: str


storage = Storage()
john = User({'id': 1, 'name': 'John', 'address': 'kirova 1'}, storage)
john.name = 'Not John'

assert john.dict() == {'id': 1, 'name': 'Not John', 'address': 'kirova 1'}
```

!!! Note
    You don't need to describe full data structure, only fields you need, rest corm leave as is. In example above `address` key


## Simple nested

```python
from corm import Storage, Entity, Nested


class Address(Entity):
    street: str
    number: int

class User(Entity):
    name: str
    address: Address = Nested(entity_type=Address)


storage = Storage()
john = User(
    data={'name': 'John', 'address': {'street': 'First', 'number': 1}},
    storage=storage,
)

assert john.address.street == 'First'
assert john.address.number == 1
```
