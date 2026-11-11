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


def _find_exact_relation(
    relations: list[Entity | EntityRef], target: Entity | EntityRef
) -> int | None:
    # A base lookup can contain subclasses, but duplicate checks use the exact type.
    target_type = type(target)
    for index, related in enumerate(relations):
        if type(related) is target_type and (related is target or related == target):
            return index
    return None


class Storage:
    def __init__(self):
        self._entities: dict[tuple[Field, t.Any], Entity] = {}
        self._relations = defaultdict(functools.partial(defaultdict, list))

    def _check_primary_key(self, field: "Field", value: t.Any) -> EntityRef:
        key = EntityRef(field, value)
        if key in self._entities:
            raise ValueError(f"{field}={value} already in storage")
        return key

    def add(self, entity: "Entity"):
        if entity.__pk_fields__:
            for field in entity.__pk_fields__:
                value = getattr(entity, field.name)
                key = self._check_primary_key(field, value)

                # resolve reference relations
                relations = self._relations.pop(key, None)

                if relations:
                    self._relations[entity] = relations

                self._entities[key] = entity

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

        if _find_exact_relation(matches, to_) is not None:
            raise ValueError(
                f"Relation type {relation_type} already exists "
                f"between {from_} and {to_}",
            )

        matches.append(to_)
        for base in _relation_base_types(target_type):
            relations[base, relation_type].append(to_)

    def get_related_entities(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[Entity],
        relation_type: t.Any,
    ) -> list[Entity]:
        return self._relations[entity][related_entity_type, relation_type]

    def get_one_related_entity(
        self,
        entity: "Entity | EntityRef",
        related_entity_type: type["Entity"],
        relation_type: t.Any,
    ) -> "Entity | None":
        entities = self._relations[entity][related_entity_type, relation_type]

        if entities:
            return entities[0]

    def remove_relation(
        self,
        from_: Entity | EntityRef,
        to_: Entity | EntityRef,
        relation_type: t.Any,
    ) -> None:
        relations = self._relations[from_]
        target_type = type(to_)
        matches = relations[target_type, relation_type]
        index = _find_exact_relation(matches, to_)
        if index is None:
            raise ValueError("list.remove(x): x not in list")

        removed = matches.pop(index)
        for base in _relation_base_types(target_type):
            related_entities = relations[base, relation_type]
            # Another class in this bucket may compare equal to the removed target.
            for index, related in enumerate(related_entities):
                if related is removed:
                    del related_entities[index]
                    break

    def remove_relations(
        self,
        entity: Entity | EntityRef,
        related_entity_type: type[Entity],
        relation_type: t.Any,
    ) -> None:
        relations = self._relations[entity]
        matches = relations[related_entity_type, relation_type]
        removed_types = {type(related) for related in matches}
        affected_types = removed_types | {
            base
            for target_type in removed_types
            for base in _relation_base_types(target_type)
        }
        affected_types.discard(related_entity_type)
        for target_type in affected_types:
            related_entities = relations[target_type, relation_type]
            related_entities[:] = [
                related
                for related in related_entities
                if type(related) not in removed_types
            ]
        matches.clear()
