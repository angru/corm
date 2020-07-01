from corm import Storage, Entity, Field


class Foo(Entity):
    inplace = 1
    in_field = Field(default=2)
    in_field_callable = Field(default=list)


storage = Storage()
foo = Foo(data={}, storage=storage)

assert foo.inplace == 1
assert foo.in_field == 2
assert foo.in_field_callable == []
