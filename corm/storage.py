import functools
import typing as t
from collections import defaultdict
from collections.abc import Hashable, Iterable

from corm.entity import Entity
from corm.exceptions import DuplicateKeyError, RelationError
from corm.fields import Field


class EntityRef(t.NamedTuple):
    field: object
    key: Hashable


_RelationTarget = Entity | EntityRef
_TargetT = t.TypeVar("_TargetT", bound=_RelationTarget)
_RelationBucket = dict[Hashable, _RelationTarget]
_RelationBuckets = defaultdict[tuple[type[object], Hashable], _RelationBucket]


def _relation_endpoint(target: _RelationTarget) -> str:
    if isinstance(target, EntityRef):
        return f"{target.field!r}={target.key!r}"
    return type(target).__name__


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


def _relation_key(target: _RelationTarget) -> Hashable:
    # Base-class buckets can contain equal targets of different concrete types.
    key = (type(target), target)
    try:
        hash(key)
    except TypeError:
        return _UnhashableRelation(target)
    return key


class Storage:
    def __init__(self) -> None:
        self._entities: dict[EntityRef, Entity] = {}
        self._relations: defaultdict[_RelationTarget, _RelationBuckets] = defaultdict(
            functools.partial(defaultdict, dict)
        )

    def _check_primary_key(
        self, field: Field, value: Hashable, entity: Entity | None = None
    ) -> EntityRef:
        key = EntityRef(field, value)
        current = self._entities.get(key)
        if current is not None and current is not entity:
            raise DuplicateKeyError(f"{field}={value} already in storage")
        return key

    def add(self, entity: Entity) -> None:
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

    def _set_primary_key(self, entity: Entity, field: Field, value: Hashable) -> None:
        origin = t.cast(str, field.origin)
        old_key = EntityRef(field, getattr(entity, field.name))
        if self._entities.get(old_key) is not entity:
            entity._data[origin] = value
            return

        new_key = self._check_primary_key(field, value, entity=entity)
        move_key = old_key != new_key
        entity._data[origin] = value
        if move_key:
            del self._entities[old_key]
            self._index_entity(new_key, entity)

    def get(self, field: object, entity_key: Hashable) -> Entity | None:
        # An annotated primary key looks like its value type on the class.
        return self._entities.get(EntityRef(field, entity_key))

    def make_key_relation(
        self,
        field_from: object,
        key_from: Hashable,
        relation_type: Hashable,
        to: Entity,
    ) -> None:
        entity: Entity | EntityRef | None = self.get(field_from, key_from)

        if entity is None:
            # if entity with that key is not present in storage yet
            # we resolve it later
            entity = EntityRef(field=field_from, key=key_from)

        self.make_relation(from_=entity, to_=to, relation_type=relation_type)

    def make_relation(
        self,
        from_: Entity | EntityRef,
        to_: Entity | EntityRef,
        relation_type: Hashable,
    ) -> None:
        # TODO: probably weakref will be better
        relations = self._relations[from_]
        target_type = type(to_)
        matches = relations[target_type, relation_type]
        key = _relation_key(to_)

        if key in matches:
            raise RelationError(
                f"Relation type {relation_type!r} already exists between "
                f"{_relation_endpoint(from_)} and {_relation_endpoint(to_)}"
            )

        matches[key] = to_
        for base in _relation_base_types(target_type):
            relations[base, relation_type][key] = to_

    def _get_relation_bucket(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[object],
        relation_type: Hashable,
    ) -> _RelationBucket:
        relations = self._relations.get(entity)
        if relations is None:
            return {}
        return relations.get((related_entity_type, relation_type), {})

    def _reorder_relations(
        self,
        entity: Entity | EntityRef,
        relation_type: Hashable,
        ordered_targets: Iterable[_RelationTarget],
    ) -> None:
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
        related_entity_type: type[_TargetT],
        relation_type: Hashable,
    ) -> list[_TargetT]:
        matches = self._get_relation_bucket(entity, related_entity_type, relation_type)
        # Storage indexes targets by their concrete type and all Entity bases.
        return t.cast("list[_TargetT]", list(matches.values()))

    def get_one_related_entity(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[_TargetT],
        relation_type: Hashable,
    ) -> _TargetT | None:
        matches = self._get_relation_bucket(entity, related_entity_type, relation_type)
        return t.cast("_TargetT | None", next(iter(matches.values()), None))

    def remove_relation(
        self,
        from_: Entity | EntityRef,
        to_: Entity | EntityRef,
        relation_type: Hashable,
    ) -> None:
        target_type = type(to_)
        relations = self._relations.get(from_)
        matches = relations.get((target_type, relation_type), {}) if relations else {}
        key = _relation_key(to_)
        if relations is None or key not in matches:
            raise RelationError(
                f"Relation type {relation_type!r} does not exist between "
                f"{_relation_endpoint(from_)} and {_relation_endpoint(to_)}"
            )

        del matches[key]
        for base in _relation_base_types(target_type):
            del relations[base, relation_type][key]

    def remove_relations(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[_RelationTarget],
        relation_type: Hashable,
    ) -> None:
        matches = self.get_related_entities(entity, related_entity_type, relation_type)
        for related in matches:
            self.remove_relation(entity, related, relation_type)
