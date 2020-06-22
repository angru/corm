## Simple relationship

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

## Manually related entities

```python
from corm import Storage, Entity, Relationship, RelationType


storage = Storage()

class Address(Entity):
    street: str
    number: int

class User(Entity):
    name: str
    address: Address = Relationship(
        entity_type=Address, relation_type=RelationType.PARENT,
    )


address = Address({'street': 'First', 'number': 1}, storage)
john = User({'name': 'John'}, storage)

storage.make_relation(
    from_=john, to_=address, relation_type=RelationType.PARENT,
)

assert john.address == address
```


## Bidirectional relationships

```python
from corm import Storage, Entity, Relationship, Nested, RelationType


storage = Storage()

class Address(Entity):
    street: str
    number: int
    user: 'User' = Relationship(
        entity_type='User', relation_type=RelationType.CHILD,
    )

class User(Entity):
    name: str
    address: Address = Nested(
        entity_type=Address, back_relation_type=RelationType.CHILD,
    )


john = User(
    data={'name': 'John', 'address': {'street': 'First', 'number': 1}},
    storage=storage,
)

assert john.address.user == john
```

## Self-nested
```python
import typing as t

from corm import Storage, Entity, Relationship, Nested, RelationType

class Item(Entity):
    id: int
    items: t.List['Item'] = Nested(
        entity_type='Item', many=True, back_relation_type=RelationType.CHILD,
    )
    parent: 'Item' = Relationship(
        entity_type='Item', relation_type=RelationType.CHILD,
    )

storage = Storage()
item1 = Item({'id': 1, 'items': [{'id': 2}, {'id': 3}]}, storage)
item2, item3 = item1.items

assert item1.id == 1
assert item1.parent is None

assert item2.id == 2
assert item2.parent == item1
assert item2.items == []

assert item3.id == 3
assert item3.parent == item1
assert item3.items == []
```
