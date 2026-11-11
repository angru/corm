# Storage

`Storage` indexes each `Field(pk=True)` independently. Assigning a new primary
key moves that field's index entry. If another entity already holds the key,
the assignment raises `ValueError` and leaves the entity and its index entries
unchanged.

`KeyNested` resolves the stored key on each read. A reference to the previous
key keeps that value. While the key is missing, reading the reference raises
`ValueError` with `required=True` (the default) or returns `None` with
`required=False`. With `many=True` and `required=False`, the result skips
missing keys. A back relation waiting for the new key attaches when the entity
takes that key, just as it does when the entity is first loaded.

```python
--8<-- "examples/storage_primary_key_change.py"
```

`Storage.get_related_entities()` returns a new list in relation insertion
order. Editing that list has no effect on storage.
