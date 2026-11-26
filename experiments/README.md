## Renumber a directory user in place

Run `python -m experiments.document_rekey` from the repository root. The
prototype accepts the Directory schema from the storage example, an existing
user and a new integer ID. It prepares raw membership records for all groups
on the user's reverse relation before changing the key. The unpaired lead is
found explicitly on the document root. Unresolved IDs, membership order and
extra keys on each record survive the change.

The two checked conflicts (an occupied ID or a duplicate membership, including
a pending one) are rejected before any write. The experiment assumes exclusive
access, a consistent graph and one directory per store. Its preflight covers
these schema-specific conflicts. A general API would need a way to discover
unpaired owners, a key-manager operation for rewriting raw records, and a
failure policy for custom callbacks. The prototype uses a private paired-field
writer and belongs to the research checkout.

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
document changes. This read-only experiment leaves custom record rewriting
and legacy reverse-index updates to a future write protocol.
