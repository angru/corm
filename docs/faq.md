# FAQ

## Is corm fast or memory-efficient?

corm is designed for convenient navigation and editing of related data in
memory. It is not optimized for speed. The storage keeps references to the
entities it indexes and the entities in its relation index.

The [benchmark](https://github.com/angru/corm/tree/master/benchmarks) measures
setup and relationship traversal for dictionaries and corm entities.

## Does corm validate input?

corm uses annotations for typed attribute access and relation inference. It
checks that required fields are present and that it can maintain declared
relationships and keys. It does not validate field value types or coerce data.

## How is this different from Pydantic?

Pydantic validates and parses input into typed models. If you want a nested
child to know its parent in Pydantic, you set up that link in application code.
corm gives the child a parent link through a paired `Nested` and
`Relationship` and resolves references by ID through `Storage`. It works
directly with the input dictionary and preserves undeclared keys by default.

## Can I use it with Pydantic or attrs models?

Yes. Validate or structure your input first, then pass a dictionary from
`model_dump()` or `attrs.asdict()` into corm. Use output keys that match your
corm fields' `origin` settings. You can also pass `entity.dict()` back to
your validation or structuring layer. corm wraps the dictionaries you pass in,
so edits through corm update those dictionaries.
