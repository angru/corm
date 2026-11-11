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
as `{"id": 123}`.

```python
--8<-- "docs/examples/key_relationships_key_manager.py"
```
