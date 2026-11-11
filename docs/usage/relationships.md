`Nested()` and `Relationship()` infer the related entity type and whether the
field holds one entity or a list. Use `Address` for a single entity and
`list[Address]` for a list. Quoted forward references such as `"Address"` and
`list["Address"]` are resolved through the entity registry when needed. Optional
annotations such as `Address | None` and `Optional[list[Address]]` infer the
same type and cardinality as their non-optional forms.

You can still pass `entity_type=` and `many=` explicitly. Each explicit
argument overrides the corresponding inference.

## Simple relationship

```python
--8<-- "examples/relationships_simple.py"
```

## Bidirectional relationships

```python
--8<-- "examples/relationships_bidirectional.py"
```

## Self-nested
```python
--8<-- "examples/relationships_self_nested.py"
```

## Change relationships between entities

```python
--8<-- "examples/relationships_change.py"
```

You can also modify or replace a relation declared as a list.

```python
--8<-- "examples/relationships_change_many.py"
```

!!! Note
    As you can see, changing the relationship through `Nested` updates both user and address.

## Manually related entities

It is not common case but is is able to use this way

```python
--8<-- "examples/relationshps_manually_related.py"
```
