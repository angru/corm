# Storage

`Storage` is an in-memory identity map and relation index. Create one
`Storage()` per loaded document and share it among that document's entities.
Nested entities inherit their owner's storage. The storage holds strong
references to indexed entities and relation endpoints, so they can live as
long as the storage does, even after you drop your own references to them.

## Primary keys

Mark a field with `Field(pk=True)` to register each entity by that field and
its value. `storage.get(User.id, 1)` returns the registered instance, or
`None` if the key is absent. A key must be hashable. corm indexes each
primary-key field separately, so two different fields can use the same key.

Creating another entity with the same key on the same field raises
`DuplicateKeyError`. Assigning a new key through an entity attribute moves
the index entry. A conflicting assignment raises the same error and leaves
the original key and index entry in place.

## Dangling key references

A `KeyNested` field can be loaded before its target. Each read looks up the
stored key in the same storage. If the key is missing, reading the field
raises `EntityNotFoundError` with the default `required=True`. Set
`required=False` to return `None` for an unresolved single reference or
skip unresolved keys in a list. The stored keys remain in the data.

Changing the target's primary key leaves existing references at their stored
values. The example shows the old reference becoming unresolved and a
reference waiting for the new key resolving to the same user.

```python
--8<-- "docs/examples/storage_primary_key_change.py"
```

## Manual relations

Use `make_relation(from_=source, to_=target, relation_type=kind)` to add a
directed link for a standalone `Relationship` with a matching
`relation_type`. Use `remove_relation` with the same arguments to unlink it.
Adding an existing link or removing a missing one raises `RelationError`.
For paired `Nested` and `KeyNested` fields, assign or edit the relation
attributes to update the payload and index together.

`get_related_entities()` returns a new list in relation order. Editing that
list leaves the storage index unchanged.

This example adds and removes a manual link from a user to an address.

```python
--8<-- "docs/examples/relationships_manually_related.py"
```
