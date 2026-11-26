# Accept two ID spellings and redact a nested field

A member import accepts either `memberId` or `id`. Other code looks up the
member by its canonical `id`. A response includes the member's profile and
omits its internal note. The note must remain available for later edits.

`load_member` copies the payload because corm wraps nested dictionaries in
place. It rejects ambiguous IDs before constructing or registering the member.
`export_member` removes the note from the dictionary that corm exported for
the declared `Nested` profile. Other keys pass through. If the response has a
fixed set of public fields, select those fields explicitly.

```python
--8<-- "docs/examples/document_transforms.py"
```

Run the example from the repository root with
`uv run --locked python -m docs.examples.document_transforms`.

## Use the same policy with cattrs

An application that already uses a cattrs `Converter` can register the two
functions for `Member`. Each structure call below loads one independent
document into a fresh store. The unstructure hook applies the response policy
when cattrs exports a member. Other code can still call `member.dict()` for a
full export.

```python
--8<-- "docs/recipes/cattrs_transforms.py"
```

Run the same assertions through cattrs with
`uv run --locked --with cattrs==26.2.1 python -m docs.recipes.cattrs_transforms`.
