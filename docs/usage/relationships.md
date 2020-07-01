## Simple relationship

```python
{!examples/relationships_simple.py!}
```

## Bidirectional relationships

```python
{!examples/relationships_bidirectional.py!}
```

## Self-nested
```python
{!examples/relationships_self_nested.py!}
```

## Change relationships between entities

```python
{!examples/relationships_change.py!}
```

Also it works with `many=True`

```python
{!examples/relationships_change_many.py!}
```

!!! Note
    As you can see it changes both user and address, but keep in mind it is possible to change relationship through `Nested` but not through `Relationship`. In this example `address.user = user` will raise `ValueError`

## Manually related entities

It is not common case but is is able to use this way

```python
{!examples/relationshps_manually_related.py!}
```
