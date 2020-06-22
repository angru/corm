## Simple case
```python
from corm import Storage, Entity, NestedKey, Field

class Entity(Entity):
    id: int = Field(pk=True)
    name: str

class EntityHolder(Entity):
    name: str
    entity: Entity = NestedKey(Entity.id, 'entity_id')

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'entity_id': 123}, storage=storage)

assert holder.entity == entity
```

## Bidirectional key relationships

```python
from corm import (
    Storage, Field, Entity, NestedKey, KeyRelationship, RelationType,
)

class Entity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: 'EntityHolder' = KeyRelationship(
        entity_type='EntityHolder', field_name='id',
        relation_type=RelationType.CHILD,
    )

class EntityHolder(Entity):
    name: str
    entity: Entity = NestedKey(
        related_entity_field=Entity.id, key='entity_id',
        back_relation_type=RelationType.CHILD,
    )

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

assert holder.entity == entity
assert entity.holder == holder
```
