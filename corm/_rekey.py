"""Internal staging for paired key-reference index moves.

The caller must keep the graph stable between preparation and commit, and must
preflight the target's primary key and any other document changes separately.
"""

from copy import deepcopy

from corm.exceptions import RelationError
from corm.fields import KeyNested
from corm.storage import _relation_key


class _PairedKeyMove:
    def __init__(self, field, storage, old_source, new_source, changes):
        self.field = field
        self.storage = storage
        self.old_source = old_source
        self.new_source = new_source
        self.changes = changes

    def commit(self):
        for owner, data in self.changes:
            self.storage.remove_relation(self.old_source, owner, self.field)
            self.storage.make_relation(self.new_source, owner, self.field)
            owner._data[self.field.origin] = data
            self.field._mark_list_changed(owner)


def _prepare_paired_key_move(field, target, old_key, new_key):
    """Stage one paired KeyNested field; do not mutate the graph or indexes."""
    if not isinstance(field, KeyNested) or field.back_populates is None:
        raise RelationError("Expected a paired KeyNested field")
    if field.back_relation or field.many not in (True, False):
        raise RelationError("Unsupported key relation shape")
    relationship = field._resolve_pair()
    if relationship.many not in (True, False):
        raise RelationError("Unsupported reverse relation shape")
    field._check_target_relationship(target)
    storage = target.storage
    if storage.get(field.related_entity_field, old_key) is not target:
        raise RelationError("Expected the target at the old key")
    storage._check_primary_key(field.related_entity_field, new_key, entity=target)
    old_source = field._key_source(old_key)
    new_source = field._key_source(new_key)
    if old_source == new_source:
        return _PairedKeyMove(field, storage, old_source, new_source, [])
    owners = storage.get_related_entities(old_source, field._declaring_owner, field)
    destination = storage._get_relation_bucket(
        new_source, field._declaring_owner, field
    )
    if owners and not relationship.many and destination:
        raise RelationError(f"Destination already has an owner for {field}")
    changes = []
    for owner in owners:
        field._check_owner(owner)
        if _relation_key(owner) in destination:
            raise RelationError(f"Owner already references destination for {field}")
        raw = owner._data.get(field.origin)
        items = list(raw) if field.many else [raw]
        rewritten = 0
        for index, item in enumerate(items):
            key = field.key_manager.get(deepcopy(item))
            if key == new_key:
                raise RelationError(f"Owner already references destination for {field}")
            if key == old_key:
                replacement = field.key_manager.rewrite_key(deepcopy(item), new_key)
                if replacement is None and not field.many:
                    raise RelationError(f"Expected a non-null key for {field}")
                if field.key_manager.get(deepcopy(replacement)) != new_key:
                    raise ValueError("Rewritten reference has the wrong key")
                items[index] = replacement
                rewritten += 1
        if rewritten != 1:
            raise RelationError(f"Inconsistent source index for {field}")
        changes.append((owner, items if field.many else items[0]))
    return _PairedKeyMove(field, storage, old_source, new_source, changes)


def rekey(storage, root, target, key_field, new_key):
    """Prepare a document-scoped key change and commit it without callbacks."""
    from corm.entity import Entity
    from corm.fields import Field, Nested
    from corm.storage import EntityRef

    if not isinstance(root, Entity) or not isinstance(target, Entity):
        raise ValueError("Root and target must be entities")
    if root.storage is not storage or target.storage is not storage:
        raise ValueError("Root and target must belong to this storage")
    if (
        not isinstance(key_field, Field)
        or not key_field.pk
        or not any(f is key_field for f in target.__fields__.values())
        or not any(f is key_field for f in target.__pk_fields__ or ())
    ):
        raise ValueError("Field must be a primary key descriptor on the target")
    old_key = getattr(target, key_field.name)
    if storage.get(key_field, old_key) is not target:
        raise RelationError("Expected the target at the old key")
    storage._check_primary_key(key_field, new_key, entity=target)

    pending = [root]
    entities = []
    seen = set()
    while pending:
        owner = pending.pop()
        if id(owner) in seen:
            continue
        if owner.storage is not storage:
            raise RelationError("Nested entity belongs to another storage")
        seen.add(id(owner))
        entities.append(owner)
        for field in owner.__fields__.values():
            if isinstance(field, Nested):
                raw = owner._data.get(field.origin)
                if raw is not None:
                    children = raw if field.many else (raw,)
                    pending.extend(
                        child for child in children if isinstance(child, Entity)
                    )
    if id(target) not in seen:
        raise ValueError("Target is not reachable from root")
    if old_key == new_key:
        return

    # A source slot can only be rewritten through one descriptor.
    slots = {}
    changes = []
    paired_fields = set()

    def claim(owner, field):
        slot = (id(owner), field.origin)
        aliases = [f for f in owner.__fields__.values() if f.origin == field.origin]
        if any(f is not field for f in aliases) or (
            slot in slots and slots[slot] is not field
        ):
            raise RelationError(f"Conflicting field aliases for {field}")
        slots[slot] = field

    claim(target, key_field)
    for owner in entities:
        for field in owner.__fields__.values():
            if (
                not isinstance(field, KeyNested)
                or field.related_entity_field is not key_field
            ):
                continue
            raw = owner._data.get(field.origin)
            if raw is None:
                continue
            items = list(raw) if field.many else [raw]
            matches = [
                i
                for i, item in enumerate(items)
                if field.key_manager.get(deepcopy(item)) == old_key
            ]
            if not matches:
                continue
            claim(owner, field)
            if field.back_relation:
                raise RelationError("Legacy reverse indexes are unsupported")
            if field.back_populates is not None:
                paired_fields.add(field)
                continue
            for i in matches:
                replacement = field.key_manager.rewrite_key(deepcopy(items[i]), new_key)
                if replacement is None and not field.many:
                    raise RelationError(f"Expected a non-null key for {field}")
                if field.key_manager.get(deepcopy(replacement)) != new_key:
                    raise ValueError("Rewritten reference has the wrong key")
                items[i] = replacement
            changes.append((owner, field.origin, items if field.many else items[0]))

    # Include indexed paired fields even when all their owners are outside root.
    for source in storage._relations:
        if (
            isinstance(source, EntityRef)
            and isinstance(source.field, KeyNested)
            and source.field.related_entity_field is key_field
            and source.key == old_key
            and source.field.back_populates is not None
        ):
            paired_fields.add(source.field)
    plans = []
    for field in paired_fields:
        owners = storage.get_related_entities(
            field._key_source(old_key), field._declaring_owner, field
        )
        if any(id(owner) not in seen for owner in owners):
            raise RelationError("Paired owner is outside the root")
        plans.append(_prepare_paired_key_move(field, target, old_key, new_key))

    storage._set_primary_key(target, key_field, new_key)
    for owner, origin, value in changes:
        owner._data[origin] = value
    for plan in plans:
        plan.commit()
