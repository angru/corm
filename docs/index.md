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
    user: 'User | None' = Relationship()

class User(Entity):
    name: str
    address: Address | None = Nested(back_populates='user')


storage = Storage()
john = User(
    data={'name': 'John', 'address': {'street': 'First', 'number': 1}},
    storage=storage,
)

assert john.address.street == 'First'
assert john.address.number == 1
assert john.address.user is john
```

`Nested` and `Relationship` infer the related entity from the field annotation.
A list annotation such as `list[Address]` also infers `many=True`. You can still
pass `entity_type=` and `many=` explicitly.
