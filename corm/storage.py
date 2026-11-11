import collections
import functools
import typing as t
from collections import defaultdict

from corm.entity import Entity

if t.TYPE_CHECKING:
    from corm.entity import Field

EntityRef = collections.namedtuple("EntityRef", ["field", "key"])


def _relation_base_types(
    entity_type: type[Entity | EntityRef],
) -> t.Iterator[type[Entity]]:
    for base in entity_type.__mro__[1:]:
        if issubclass(base, Entity):
            yield base


class _UnhashableRelation:
    # Preserve equality-based membership for targets without a hash.
    def __init__(self, target: Entity | EntityRef):
        self.target = target

    def __hash__(self):
        return hash(type(self.target))

    def __eq__(self, other):
        if not isinstance(other, _UnhashableRelation):
            return NotImplemented
        return type(self.target) is type(other.target) and (
            self.target is other.target or self.target == other.target
        )


def _relation_key(target: Entity | EntityRef):
    # Base-class buckets can contain equal targets of different concrete types.
    key = (type(target), target)
    try:
        hash(key)
    except TypeError:
        return _UnhashableRelation(target)
    return key


class Storage:
    def __init__(self):
        self._entities: dict[EntityRef, Entity] = {}
        self._relations = defaultdict(functools.partial(defaultdict, dict))

    def _check_primary_key(
        self, field: "Field", value: t.Any, entity: Entity | None = None
    ) -> EntityRef:
        key = EntityRef(field, value)
        current = self._entities.get(key)
        if current is not None and current is not entity:
            raise ValueError(f"{field}={value} already in storage")
        return key

    def add(self, entity: "Entity"):
        keys = [
            self._check_primary_key(field, getattr(entity, field.name))
            for field in entity.__pk_fields__ or ()
        ]
        for key in keys:
            self._index_entity(key, entity)

    def _index_entity(self, key: EntityRef, entity: Entity) -> None:
        pending = self._relations.pop(key, None)
        if pending:
            current = self._relations.get(entity)
            if current is None:
                self._relations[entity] = pending
            else:
                for relation, matches in pending.items():
                    bucket = current[relation]
                    for target_key, target in matches.items():
                        bucket.setdefault(target_key, target)
        self._entities[key] = entity

    def _set_primary_key(self, entity: Entity, field: "Field", value: t.Any) -> None:
        old_key = EntityRef(field, getattr(entity, field.name))
        if self._entities.get(old_key) is not entity:
            entity._data[field.origin] = value
            return

        new_key = self._check_primary_key(field, value, entity=entity)
        move_key = old_key != new_key
        entity._data[field.origin] = value
        if move_key:
            del self._entities[old_key]
            self._index_entity(new_key, entity)

    def get(self, field, entity_key) -> "Entity":
        return self._entities.get(EntityRef(field, entity_key))

    def make_key_relation(
        self,
        field_from: "Field",
        key_from: t.Any,
        relation_type: t.Any,
        to: "Entity",
    ):
        entity = self.get(field_from, key_from)

        if entity is None:
            # if entity with that key is not present in storage yet
            # we resolve it later
            entity = EntityRef(field=field_from, key=key_from)

        self.make_relation(from_=entity, to_=to, relation_type=relation_type)

    def make_relation(
        self,
        from_: "Entity | EntityRef",
        to_: "Entity | EntityRef",
        relation_type: t.Any,
    ):
        # TODO: probably weakref will be better
        relations = self._relations[from_]
        target_type = type(to_)
        matches = relations[target_type, relation_type]
        key = _relation_key(to_)

        if key in matches:
            raise ValueError(
                f"Relation type {relation_type} already exists "
                f"between {from_} and {to_}",
            )

        matches[key] = to_
        for base in _relation_base_types(target_type):
            relations[base, relation_type][key] = to_

    def _get_relation_bucket(self, entity, related_entity_type, relation_type):
        relations = self._relations.get(entity, {})
        return relations.get((related_entity_type, relation_type), {})

    def _reorder_relations(self, entity, relation_type, ordered_targets):
        relations = self._relations[entity]
        for target in ordered_targets:
            key = _relation_key(target)
            target_type = type(target)
            for entity_type in (target_type, *_relation_base_types(target_type)):
                bucket = relations[entity_type, relation_type]
                bucket[key] = bucket.pop(key)

    def get_related_entities(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[Entity],
        relation_type: t.Any,
    ) -> list[Entity]:
        matches = self._get_relation_bucket(entity, related_entity_type, relation_type)
        return list(matches.values())

    def get_one_related_entity(
        self,
        entity: "Entity | EntityRef",
        related_entity_type: type["Entity"],
        relation_type: t.Any,
    ) -> "Entity | None":
        matches = self._get_relation_bucket(entity, related_entity_type, relation_type)
        return next(iter(matches.values()), None)

    def remove_relation(
        self,
        from_: Entity | EntityRef,
        to_: Entity | EntityRef,
        relation_type: t.Any,
    ) -> None:
        target_type = type(to_)
        relations = self._relations.get(from_, {})
        matches = relations.get((target_type, relation_type), {})
        key = _relation_key(to_)
        if key not in matches:
            raise ValueError("list.remove(x): x not in list")

        del matches[key]
        for base in _relation_base_types(target_type):
            del relations[base, relation_type][key]

    def remove_relations(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[Entity],
        relation_type: t.Any,
    ) -> None:
        matches = self.get_related_entities(entity, related_entity_type, relation_type)
        for related in matches:
            self.remove_relation(entity, related, relation_type)
