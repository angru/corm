`KeyNested` takes the related entity's primary-key field as its
`related_entity_field` argument. It infers `many=True` from list annotations
such as `list[Address]` or `list["Address"]`. You can still pass `many=` to
set this explicitly.

## Simple case
```python
--8<-- "examples/key_relationships_simple.py"
```

## Bidirectional key relationships

```python
--8<-- "examples/key_relationships_bidirectional.py"
```


## Change relationships between entities
As with `Nested` it is possible to change related data

```python
--8<-- "examples/key_relationships_change.py"
```
