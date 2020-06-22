import typing as t

from corm import Storage, Entity, Field, Nested, RelationType, Relationship


def test_nested():
    storage = Storage()

    class Address(Entity):
        street: str

    class User(Entity):
        id: int
        name: str = Field(default='Bob')
        address: Address = Nested(entity_type=Address)

    john = User(
        data={
            'id': 1,
            'name': 'John',
            'description': 'john smith',
            'address': {
                'street': 'kirova',
            },
        },
        storage=storage,
    )

    assert john.address.street == 'kirova'


def test_self_related():
    class Item(Entity):
        id: int
        items: t.List['Item'] = Nested(    # noqa: F821
            entity_type='Item',
            many=True,
            back_relation_type=RelationType.CHILD,
        )
        parent: 'Item' = Relationship(
            entity_type='Item',
            relation_type=RelationType.CHILD,
        )    # noqa: F821

    storage = Storage()
    item1 = Item({'id': 1, 'items': [{'id': 2}, {'id': 3}]}, storage)
    item2, item3 = item1.items

    assert item1.id == 1
    assert item1.parent is None

    assert item2.id == 2
    assert item2.parent == item1
    assert item2.items == []

    assert item3.id == 3
    assert item3.parent == item1
    assert item3.items == []
