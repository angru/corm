_Relationships between entities_

[![build](https://github.com/angru/corm/workflows/build/badge.svg)](https://github.com/angru/corm/actions?query=workflow%3Abuild+branch%3Amaster++)

## Installation

`pip install corm`

## Example

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