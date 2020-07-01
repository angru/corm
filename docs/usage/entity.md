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

## Fields

To set additional settings for any entity fields there is `Field` class

```python
{!examples/entity_fields.py!}
```

## Default values

There are two ways to set default value, just set as class value or through `default` param of `Field`, `Nested` or `KeyNested`

```python
{!examples/entity_default_values.py!}
```

!!! Note
    `default` also can be callable, corm call it each time when creating entity instance if value of field is not provided. But you can use it only with `Field`, `Nested` or `KeyNested`, inplace is not allowed

```python
{!examples/entity_default_callable_inplace.py!}
```
