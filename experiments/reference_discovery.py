"""Locate stored unpaired key references in a single loaded document."""

from collections.abc import Hashable, Iterator
from copy import deepcopy
from typing import NamedTuple

from corm import Entity, KeyNested, Nested


class Reference(NamedTuple):
    owner: Entity
    field: KeyNested
    index: int | None


def unpaired_references(
    root: Entity, key_field: object, key: Hashable
) -> Iterator[Reference]:
    pending = [root]
    seen: set[int] = set()
    while pending:
        owner = pending.pop()
        if id(owner) in seen or owner.storage is not root.storage:
            continue
        seen.add(id(owner))
        for field in owner.__fields__.values():
            raw = owner._data.get(field.origin)
            if raw is None:
                continue
            if isinstance(field, Nested):
                children = raw if field.many else (raw,)
                pending.extend(child for child in children if isinstance(child, Entity))
            elif (
                isinstance(field, KeyNested)
                and field.back_populates is None
                and field.related_entity_field is key_field
            ):
                if field.many:
                    for index, record in enumerate(raw):
                        if field.key_manager.get(deepcopy(record)) == key:
                            yield Reference(owner, field, index)
                elif field.key_manager.get(deepcopy(raw)) == key:
                    yield Reference(owner, field, None)
