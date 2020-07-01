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

## Storage context

```python
from corm import Entity, storage_ctx

class User(Entity):
    id: int


with storage_ctx:
    user = User(data={'id': 1})

```

## Namespaces

Right now it is not possible to define few entities with same name, for example there are two files:

_a.py_
```python
from corm import Entity

class Foo(Entity):
    id: int
```
and same in _b.py_ will cause error
```python
from corm import Entity

class Foo(Entity):
    id: int
```

Solution

```python
from corm import Entity, Namespace

namespace1 = Namespace()
namespace2 = Namespace()

# a.py
class Foo(Entity):
    class Config:
        namespace = namespace1

    id: int

# b.py
class Foo(Entity):
    class Config:
        namespace = namespace2

    id: int
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
