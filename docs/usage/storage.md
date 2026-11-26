# Storage

`Storage` is an in-memory identity map and relation index. Create one
`Storage()` per loaded document and share it among that document's entities.
Nested entities inherit their owner's storage. The storage holds strong
references to indexed entities and relation endpoints, so they can live as
long as the storage does, even after you drop your own references to them.

## Storage for concurrent work

Create the store where your application starts processing a document. Pass
it to the functions that construct or look up its entities. An HTTP handler,
a queue consumer and a batch job can all use the same functions. If a request
contains two documents with independent ID spaces, give each its own store.

In this example two tasks load different users with ID 7. The barrier makes
both tasks finish registering their user before either resolves its ticket.
Each ticket finds the user from its own document.

```python
--8<-- "docs/examples/storage_request_scope.py"
```

When a child task continues work on the same document, pass it the same
store deliberately. For an independent job, create a fresh store in that
job. If an application uses a Python `ContextVar` to carry the store,
`asyncio.create_task()` copies the binding by default. The child still holds
the same mutable `Storage` after the parent resets its binding. Resetting the
parent's context cannot undo writes the child makes to that store.

The [FastAPI recipe](../recipes/fastapi.md) shows the same ownership rule
in a web request.

## Copy a document into another store

To edit an independent copy, export the document root, deep-copy the
payload, and load it into a fresh `Storage`. Include the owners and targets
of the links you want to rebuild. In this example each board contains its
own user 7 and ticket. Editing the copied ticket's labels leaves the
original list intact. The deep copy matters because ordinary mutable field
values can be shared with the dictionary returned by `dict()`.

```python
--8<-- "docs/examples/storage_copy_document.py"
```

Use this recipe for dictionary data that the destination model can load.
If a field exports under a different key from the one it accepts, map
the keys before loading. A `KeyNested` reference exports its stored ID
with the default access mode. Copying a ticket alone makes it look up that ID
in the destination. Supply the intended user there before reading the
required link. Reverse links from paired fields are rebuilt when their
owning data is loaded. Recreate manually indexed links separately.

A duplicate primary key raises `DuplicateKeyError`. In a multi-entity
load, a child processed before the collision may already be indexed.
If a failed import must leave a live graph intact, build the complete
candidate in a fresh store, check the required links, and switch the
application's root reference only after success. This replaces the graph
with new Python objects. Existing references still point to the old ones.

Assigning `entity.storage` changes the attribute while the original store
still indexes the object. Calling `destination.add(entity)` can then leave
the same object indexed in both stores. Use reconstruction when you need
independent graphs.

## Primary keys

Mark a field with `Field(pk=True)` to register each entity by that field and
its value. `storage.get(User.id, 1)` returns the registered instance, or
`None` if the key is absent. A key must be hashable. corm indexes each
primary-key field separately, so two different fields can use the same key.

Creating another entity with the same key on the same field raises
`DuplicateKeyError`. Assigning a new key through an entity attribute moves
the index entry. A conflicting assignment raises the same error and leaves
the original key and index entry in place.

## Finding the first matching entity

Choose the collection to search. A Python generator can filter a document's
nested users, including users without primary keys. `next(..., None)` returns
the first match in collection order or `None` if the name is absent. Creating
another user in the same store leaves the document's list unchanged.

```python
--8<-- "docs/examples/query_collection.py"
```

When the caller knows a primary key, `store.get(Member.id, 7)` goes directly
to the identity index. An entity with two primary-key fields can be looked up
through either field. A standalone user without a primary key has no entry in
that index. For a name search, compare `user.name` on each instance. Comparing
`User.name` to a string evaluates immediately to a boolean.

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

## Renumbering a referenced entity

When the application knows the owners, it can keep the same Python object:
capture the owners before changing its ID, change the ID, then reassign
their key fields to the entity. The example above does this for scalar
paired references. Include unpaired owners explicitly because they may have
no reverse field. For a list of fully resolved plain keys, capture the
ordered targets before the change and assign the list back afterwards.
Whole-list assignment rebuilds the serialized keys. Omitted unresolved
entries and extra metadata on rebuilt key objects can be lost.

When a document needs all edits to succeed together, prepare a replacement
using its known schema. In this directory, user IDs appear in three places:
the user records, the scalar `lead_id`, and the `user_id` in each group's
ordered membership records. Change those keys in a deep copy so ranks,
unrelated values and pending IDs survive. Load the candidate in a fresh
store and check required links before replacing the application's root.

```python
--8<-- "docs/examples/storage_renumber_user.py:migration"
```

The [runnable example](../examples/storage_renumber_user.py) changes user 1
to 5. Two other attempts fail: ID 2 belongs to another user, and ID 9
already appears as a pending member in the same paired list. The latter
would create a duplicate membership. Both failures leave the original
directory's data, lookups and reverse links intact. A reference already
waiting for the new ID elsewhere can become resolved, as in the address
example above. This application-level migration covers the directory passed
to it and returns new Python objects.

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
