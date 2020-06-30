## Simple case
```python
from corm import Storage, Entity, KeyNested, Field

class Entity(Entity):
    id: int = Field(pk=True)
    name: str

class EntityHolder(Entity):
    name: str
    entity: Entity = KeyNested(Entity.id, 'entity_id')

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'entity_id': 123}, storage=storage)

assert holder.entity == entity
```

## Bidirectional key relationships

```python
from corm import (
    Storage, Field, Entity, KeyNested, Relationship, RelationType,
)

class Entity(Entity):
    id: int = Field(pk=True)
    name: str
    holder: 'EntityHolder' = Relationship(
        entity_type='EntityHolder',
        relation_type=RelationType.RELATED,
    )

class EntityHolder(Entity):
    name: str
    entity: Entity = KeyNested(
        related_entity_field=Entity.id, key='entity_id',
        back_relation=RelationType.RELATED,
    )

storage = Storage()
entity = Entity({'id': 123, 'name': 'entity'}, storage=storage)
holder = EntityHolder({'name': 'holder', 'entity_id': 123}, storage=storage)

assert holder.entity == entity
assert entity.holder == holder
```
