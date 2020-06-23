## Base usage

You can describe wrappers for data structures with `Entity`

```python
from corm import Storage, Entity


class User(Entity):
    id: int
    name: str
    description: str = 'cool guy'


storage = Storage()
john = User({'id': 1, 'name': 'John', 'address': 'kirova 1'}, storage)
john.name = 'Not John'

assert john.dict() == {
    'id': 1, 'name': 'Not John',
    'address': 'kirova 1', 'description': 'cool guy',
}
```

!!! Note
    You don't need to describe full data structure, only fields you need, rest corm leave as is. In example above `address` key
