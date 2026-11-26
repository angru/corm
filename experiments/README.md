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
