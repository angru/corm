from corm import Entity, Nested, Relationship, Storage


class Item(Entity):
    id: int
    items: list["Item"] = Nested(back_populates="parent", default=list)
    parent: "Item | None" = Relationship()


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

item3.items.append(item2)
assert item2.parent is item3
assert item1.items == [item3]

item2.parent = item1
assert item1.items == [item3, item2]
assert item3.items == []
