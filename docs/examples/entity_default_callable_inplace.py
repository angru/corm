from corm import Storage, Entity


class Foo(Entity):
    inplace = list


storage = Storage()
foo = Foo(data={}, storage=storage)

assert foo.inplace is list  # still callable, not new empty list
