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
