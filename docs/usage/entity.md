# Entities

An `Entity` wraps a dictionary. Declare the fields you want to access as
attributes, then pass the dictionary and a `Storage` to the entity constructor.
Attribute writes update the wrapped dictionary. Undeclared keys stay in the
data and are included in `entity.dict()`.

## Field declarations

An explicit `Field` or relation descriptor becomes a field. A public
annotation such as `name: str` declares a field, and a public class value such
as `description = "Project member"` supplies a default. Unannotated methods,
properties, other callables, and names starting with `_` stay out of the
implicit field declarations. Annotations describe field types for editors and
type checkers. corm uses relation annotations to infer related entity types and
whether a field holds one entity or a list.

## Input and output keys

`origin` is the dictionary key a field reads and writes. It defaults to the
attribute name. `destination` is the key used by `dict()` and defaults to
`origin`. When they differ, the export uses the destination key in place of
the origin. Load the export with a model that expects the destination key, or
map it back before reloading with the same model.

## Access and export

`Field` and `Nested` default to `AccessMode.ALL`. Combine `AccessMode` flags
with `|`. `LOAD` processes the field at construction, `SET` permits assignment,
and `DUMP` exports the field through its declared destination. The `GET` flag
describes a readable field. The current descriptors still allow direct reads
without it. `KeyNested` defaults to `GET_SET_LOAD` so the original key stays
in the exported data. A reverse `Relationship` lives in the relation index.

`dict(strip_none=True)` omits declared fields with `DUMP` whose value is
`None`, including fields in declared nested entities. Undeclared keys with
`None` values are preserved.

The example reads an ID from `user_id`, exports it as `id`, and uses a
read-only display name. It also shows an optional field and an undeclared key.

```python
--8<-- "docs/examples/entity_fields.py"
```

## Default values

Supply a plain class value or pass `default=` to `Field`, `Nested`, or
`KeyNested`. corm calls a default factory for each instance whose input lacks
that field. An explicit `None` value in the input counts as a supplied value.

```python
--8<-- "docs/examples/entity_default_values.py"
```

A callable assigned directly to the class remains a class attribute. Use
`Field(default=list)` if you want corm to call `list` as a field's default
factory.

```python
--8<-- "docs/examples/entity_default_callable_inplace.py"
```
