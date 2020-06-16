# corm

Библиотека для создания обьектных оберток над структурами данных и описания связей между ними

https://github.com/angru/corm/workflows/python-package/badge.svg

# Мотивация

* сложно помнить ключи словарей, если структура данных большая
* организация двусторонних связей между сущностями, особенно иерархических структурах данных
* возможность разделить безнес-логику и технические детали связывания сущностей друг с другом и поиска связанной сущности

# Возможности

## Простая модель
```python
from corm import Storage, Model, Field


storage = Storage()

class User(Model):
    id: int = Field(pk=True)
    name: str

john = User({'id': 1, 'name': 'John'}, storage)

assert john.id == 1
assert john.name == 'John'
assert john.dict() == {'id': 1, 'name': 'John'}
assert storage.get(User.id, 1) == john

# не обязательно описывать структуру данных, можно только те поля, 
# которые нужны для работы в данный момент
# при преобразовании в словарь все равно вернется исходный набор данных 

storage = Storage()

class User(Model):
    id: int = Field(pk=True)
    name: str

john = User({'id': 1, 'name': 'John', 'address': 'kirova 1'}, storage)
assert john.dict() == {'id': 1, 'name': 'John', 'address': 'kirova 1'}
```  

## Связи между сущностями
```python
from corm import Storage, Model, Relationship, RelationType


storage = Storage()

class Address(Model):
    street: str
    number: int

class User(Model):
    name: str
    address: Address = Relationship(entity_type=Address, relation_type=RelationType.PARENT)


address = Address({'street': 'First', 'number': 1}, storage)
john = User({'name': 'John'}, storage)

storage.make_relation(from_=john, to_=address, relation_type=RelationType.PARENT)

assert john.address == address
```

## Вложенные сущности
```python
from corm import Storage, Model, Nested


storage = Storage()

class Address(Model):
    street: str
    number: int

class User(Model):
    name: str
    address: Address = Nested(entity_type=Address)


john = User({'name': 'John', 'address': {'street': 'First', 'number': 1}}, storage)

assert john.address.street == 'First'
assert john.address.number == 1
```

## Двусторонние связи

```python
from corm import Storage, Model, Relationship, Nested, RelationType


storage = Storage()

class Address(Model):
    street: str
    number: int
    user: 'User' = Relationship(entity_type='User', relation_type=RelationType.CHILD)

class User(Model):
    name: str
    address: Address = Nested(entity_type=Address, back_relation_type=RelationType.CHILD)


john = User({'name': 'John', 'address': {'street': 'First', 'number': 1}}, storage)

assert john.address.user == john
```

## Самовложенные сущности
```python
import typing as t

from corm import Storage, Model, Relationship, Nested, RelationType

class Item(Model):
    id: int
    items: t.List['Item'] = Nested(entity_type='Item', many=True, back_relation_type=RelationType.CHILD)
    parent: 'Item' = Relationship(entity_type='Item', relation_type=RelationType.CHILD)

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

## Связи по ключу
```python
from corm import Storage, Model, NestedKey, Field

class Entity(Model):
    id: int = Field(pk=True)
    name: str

class EntityHolder(Model):
    name: str
    entity: Entity = NestedKey(Entity.id, 'entity_id')

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'entity_id': 123}, storage=storage)

assert holder.entity == entity
```

## Двусторонние связи по ключу

```python
from corm import Storage, Field, Model, NestedKey, KeyRelationship, RelationType

class Entity(Model):
    id: int = Field(pk=True)
    name: str
    holder: 'EntityHolder' = KeyRelationship(
        entity_type='EntityHolder', field_name='id', relation_type=RelationType.CHILD,
    )

class EntityHolder(Model):
    name: str
    entity: Entity = NestedKey(
        related_entity_field=Entity.id, key='entity_id', back_relation_type=RelationType.CHILD,
    )

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

assert holder.entity == entity
assert entity.holder == holder
```


# TBD

## Хуки

```python
import typing as t

from corm import Storage, Model, Nested, Hook

storage = Storage()

class Address(Model):
    id: int
    street: str
    number: int

class User(Model):
    id: int
    name: str
    address: Address = Nested(entity_type=Address)


class ExcludeHook(Hook):
    match_entities = [User, Address]

    def __init__(self, exclude_fields: t.List[str]):
        self.exclude_fields = exclude_fields
    
    def go(self, data, entity):
        if type(entity) in self.match_entities:
            for field in self.exclude_fields:
                data.pop(field, None)
        
        return data

john = User({'id': 1, 'name': 'John', 'address': {'id': 2, 'street': 'First', 'number': 1}}, storage)

assert john.dict(hooks=[ExcludeHook(exclude_fields=['id'])]) == {
    'name': 'John', 
    'address': {'street': 'First', 'number': 1},
}
```

## Изменение данных через связи

```python
import typing as t

from corm import Storage, Model, Nested


storage = Storage()

class Address(Model):
    street: str
    number: int

class User(Model):
    name: str
    addresses: t.List[Address] = Nested(entity_type=Address, many=True)


john = User(data={'name': 'John', 'addresses': [{'street': 'First', 'number': 1}]}, storage=storage)

additional_address = Address(data={'street': 'Second', 'number': 2}, storage=storage) 

john.addresses.append(additional_address)

assert john.dict() == {
    'name': 'John', 
    'addresses': [
        {'street': 'First', 'number': 1},
        {'street': 'Second', 'number': 2},
    ],
}
```

## Миграция экземпляров сущностей между хранилищами

```python
from corm import Storage, Model, Field


class User(Model):
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
from corm import Storage, Model

class User(Model):
    name: str

storage = Storage()
john = User(data={'name': 'John'}, storage=storage)
user = storage.select(User).filter(User.name == 'John').first()

assert user == john
```