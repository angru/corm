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

Also it works with `many=True`

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
