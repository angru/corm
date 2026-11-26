# Key relationships

`KeyNested` takes the related entity's primary-key field as its
`related_entity_field` argument. It infers `many=True` from list annotations
such as `list[Address]` or `list["Address"]`. You can still pass `many=` to
set this explicitly.

## Resolve a list of keys

Use `origin` when the input key name differs from the attribute name. This
example reads the `entity_ids` list and resolves each ID to a stored entity.
Access the resulting list through `holder.entities`.

```python
--8<-- "docs/examples/key_relationships_simple.py"
```

## Bidirectional key relationships

Set `back_populates` on `KeyNested` to name the `Relationship` on the
entity referenced by the key. The reverse field's annotation or `many=`
setting controls whether it returns a single owner or a list of owners.
An owner can be loaded before the related entity. Its reverse link is
available when that key appears in storage.

If the target inherits its primary-key field, annotate the `KeyNested`
attribute with the target subclass to select its `Relationship`.

```python
--8<-- "docs/examples/key_relationships_bidirectional.py"
```

## Change relationships between entities

Writing through either field updates the owner's stored key. Assign an owner
to a single `Relationship` to move the link, or assign `None` to clear it.
For a reverse list, append or remove owners or assign the replacement list.
If the owning `KeyNested` field is a list, the operation adds or removes the
corresponding key. With `required=False`, edits to the list of resolved
entities preserve keys that are still missing. Assigning a replacement list
directly to the owning field replaces its stored keys.

```python
--8<-- "docs/examples/key_relationships_change.py"
```

## Keys stored as objects

Pass a `KeyManager` when a reference is stored in a shape other than a bare
key. Implement `get(data)` to extract the hashable key used by `Storage` and
`prepare_to_set(entity)` to produce the stored representation when assigning
an entity. A list relation calls these methods for each reference. Return
`None` from `prepare_to_set(None)` for a cleared single reference.

This example reads and writes team member references stored as objects such
as `{"entity_id": 123}`. The reference key can differ from the primary-key
field on the related entity. Loading and exporting keeps extra keys such as
`rank` on the original reference. Replacing the whole list calls
`prepare_to_set` for each assigned entity, so the new references contain
only what that method returns.

```python
--8<-- "docs/examples/key_relationships_key_manager.py"
```

## Keeping metadata when a list changes

Suppose two references to user 1 have ranks 10 and 11. Assigning a list
containing just that user gives a key manager the same `User` object for
either choice. If the caller needs to keep the rank-11 entry, model each
reference as a nested entity with its own `rank` and a `KeyNested` link
to the user. The caller can then select the exact membership to keep.
An unresolved membership can also be kept explicitly until its user loads.

```python
--8<-- "docs/examples/key_relationships_membership.py"
```

For an existing `list[User]` field backed by object-shaped keys, choose
the operation according to the intended edit:

| Operation | Effect on the stored references |
| --- | --- |
| Assign a plain list, e.g. `team.users = [lee, amina]` | Rebuilds the key objects through `prepare_to_set`. Drops old references absent from the replacement, including unresolved IDs. |
| Edit a paired field, e.g. `team.users[:] = [lee, amina]` | With `back_populates` and `required=False`, keeps the old key objects for retained users and keeps unresolved references. New users get new key objects. Duplicate targets raise `RelationError`. |
| Edit the result of an unpaired lookup, e.g. `team.users.reverse()` | Reorders a temporary list. The stored references keep their original order and metadata. |
