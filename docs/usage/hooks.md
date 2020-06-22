## Simple example

```python
import typing as t

from corm import Storage, Entity, Nested, Hook, HookContext

storage = Storage()

class Address(Entity):
    id: int
    street: str
    number: int

class User(Entity):
    id: int
    name: str
    address: Address = Nested(entity_type=Address)


class ExcludeHook(Hook):
    match_entities = [User, Address]

    def __init__(self, exclude_fields: t.List[str], match_entities=None):
        super().__init__(match_entities)

        self.exclude_fields = exclude_fields

    def match(self, data, context: HookContext):
        for field in self.exclude_fields:
            data.pop(field, None)

        return data

john = User(
    data={
        'id': 1, 'name': 'John',
        'address': {'id': 2, 'street': 'First', 'number': 1},
    },
    storage=storage,
)

assert john.dict(hooks=[ExcludeHook(exclude_fields=['id'])]) == {
    'name': 'John',
    'address': {'street': 'First', 'number': 1},
}
```
