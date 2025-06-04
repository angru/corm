import typing as t

from corm import Storage, Entity, Relationship, Nested


class Item(Entity):
    id: int
    items: t.List["Item"] = Nested(
        entity_type="Item",
        back_relation=True,
        many=True,
        default=list,
    )
    parent: "Item" = Relationship(entity_type="Item")


storage = Storage()
item1 = Item({"id": 1, "items": [{"id": 2}, {"id": 3}]}, storage)
item2, item3 = item1.items

assert item1.id == 1
assert item1.parent is None

assert item2.id == 2
assert item2.parent == item1
assert item2.items == []

assert item3.id == 3
assert item3.parent == item1
assert item3.items == []
