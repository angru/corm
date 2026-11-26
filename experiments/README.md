## Renumber a directory user in place

Run `python -m experiments.document_rekey` from the repository root. The
prototype accepts the Directory schema from the storage example, an existing
user and a new integer ID. It prepares raw membership records for all groups
on the user's reverse relation before changing the key. The same operation discovers the root lead and unpaired references in loaded
nested entities. It stages one replacement per owning field, including every
matching list position. Unresolved IDs, membership order and
extra keys on each record survive the change.

The two checked conflicts (an occupied ID or a duplicate membership, including
a pending one) are rejected before any write. The experiment assumes exclusive
access, a consistent graph, distinct source keys for the rewritten fields and
one directory per store. The experiment uses the internal paired-key move plan for Group.members; the
plan supports scalar and list owners with scalar or list reverse fields.
Matching
unpaired fields with legacy reverse indexes raise before the commit.

The example's `MemberKey.rewrite_key(record, new_key)` receives a deep copy
of a matching record. Custom managers supply this method. The default manager
stores the integer ID directly. The manager can edit that copy in place or return
a replacement. Its `get` must read the requested ID from the result.
All manager calls finish before the prototype updates the user, the lead,
the membership records and their reverse index. An exception discards the
prepared copies, including changes to nested metadata in earlier groups.

This protocol assumes plain copyable document data and callbacks whose writes
are confined to their input. External side effects are outside its scope.
The plan preserves destination pending owners for a many-valued reverse and
rejects collisions for an exclusive reverse. It requires a stable, consistent
graph between preparation and commit and does not discover paired fields or
provide a general transaction. Legacy reverse indexes are unsupported.

## Discover unpaired owners before a rekey

`unpaired_references(root, User.id, old_id)` in `reference_discovery.py`
yields the owner, field and raw list index (`None` for a scalar) of each
matching occurrence. It follows loaded `Nested` children in the root's store,
visits shared or cyclic entities once, and matches the primary-key descriptor
by identity. It reads each field's source key and uses its key manager to
extract IDs, so unresolved references and duplicate list entries are visible.

Discovery assumes a stable document and a side-effect-free key-manager
`get`. Its cost is linear in visited entities, fields and membership records.
Standalone owners elsewhere in the store need their own root. Paired links
remain discoverable via their reverse field. Keep raw indices only until the
document changes. The executable scenario renumbers one user across a root,
a paired group and two nested review lists. It also injects an exception on
the final review record and checks the original export and indexes.

## Enumerate indexed entities from a store

Run `python -m experiments.entity_enumeration`. This research prototype adapts
`benchmarks.query_scope.indexed_users` to accept an entity class. It scans the
private primary-key index of one `Storage`, includes instances of subclasses,
and yields each object once by identity even if it has several indexed keys.
Only entities with at least one registered primary-key entry are discoverable;
unkeyed entities, pending references and entities in other stores are absent.
Iteration scans the live index. Collect it into a list to capture the result
at a point in time. Do not mutate the index while consuming the iterator.

Index order is the insertion order of the first surviving entry for each object,
not a stable entity registration order. A key change removes and reinserts that
entry: a single-key entity can move to the end, while another key can keep a
multi-key entity in its earlier position. Moving its last original entry can
then change its position. The executable checks these cases with `Storage.rekey`. These observations depend on private implementation details and
are not a compatibility guarantee.

The alternative sorts the enumerated snapshot by a caller-supplied key. A
stable, unique key that does not change across rekeys gives repeatable ordering
for the same set of entities. If keys tie, Python's stable sort preserves index
order among ties, so their order can still change; changing the sort key or the
set also changes the result. Scanning costs O(K) time for K index entries and
O(U) identity memory for U matching objects. Sorting adds O(U log U) time and
O(U) result space, plus the cost of computing keys. Index order avoids sorting
and can yield incrementally, but still scans unrelated entries and keeps the
identity set. Neither approach adds an index or changes normal index behavior.
