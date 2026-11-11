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

Set `back_populates` on the `Nested` field to name the `Relationship` on
the related entity. Each pair has its own links, so fields such as
`Order.billing` and `Order.shipping` can both point to `Address` and
have separate reverse fields.

The reverse field's annotation or `many=` setting controls whether it
returns one owner or a list of owners. corm resolves the pair when the first
owning entity is created, which allows forward references. Target subclasses
can use the pair by inheriting its `Relationship`.

```python
--8<-- "examples/relationships_bidirectional.py"
```

## Self-nested

A pair can connect two fields on the same entity class. Appending a child to
another parent's list or assigning its `parent` moves it from its old parent.

```python
--8<-- "examples/relationships_self_nested.py"
```

## Change relationships between entities

You can write through either field. Assign a new owner to a single
`Relationship` to move the related entity, or assign `None` to unlink it.
If the new owner holds a single value, the move replaces that value and
clears the displaced entity's reverse link.

```python
--8<-- "examples/relationships_change.py"
```

On either side, a list can be edited in place or replaced. Appending or
removing an owner through a reverse list updates that owner's field.

```python
--8<-- "examples/relationships_change_many.py"
```

The older `back_relation` parameter still works and emits a
`DeprecationWarning`. To migrate, replace it with
`back_populates="reverse_field_name"`.

## Manually related entities

A standalone `Relationship` can still use `relation_type` to read and write
links managed directly by `Storage`.

```python
--8<-- "examples/relationshps_manually_related.py"
```
