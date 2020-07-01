_Data structures relationships made easy_

[![build](https://github.com/angru/corm/workflows/build/badge.svg)](https://github.com/angru/corm/actions?query=workflow%3Abuild+branch%3Amaster++)
[![codecov](https://codecov.io/gh/angru/corm/branch/master/graph/badge.svg)](https://codecov.io/gh/angru/corm)

!!! Note
    corm is in early development. API can change.

## Installation

`pip install corm`

## Example

```python
from corm import Storage, Entity, Nested, Relationship


class Address(Entity):
    street: str
    number: int
    user: 'User' = Relationship(entity_type='User')

class User(Entity):
    name: str
    address: Address = Nested(entity_type=Address, back_relation=True)


storage = Storage()
john = User(
    data={'name': 'John', 'address': {'street': 'First', 'number': 1}},
    storage=storage,
)

assert john.address.street == 'First'
assert john.address.number == 1
assert john.address.user is john
```
