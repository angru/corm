import typing as t

import pytest

from corm import Storage, Entity, Field, Nested, Relationship


def test_nested():
    storage = Storage()

    class Address(Entity):
        street: str

    class User(Entity):
        id: int
        name: str = Field(default="Bob")
        address: Address = Nested(entity_type=Address)

    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "address": {
                "street": "kirova",
            },
        },
        storage=storage,
    )

    assert john.address.street == "kirova"


def test_self_related():
    class Item(Entity):
        id: int = Field(pk=True)
        items: t.List["Item"] = Nested(  # noqa: F821
            entity_type="Item",
            many=True,
            back_relation=True,
            default=list,
        )
        parent: "Item" = Relationship(entity_type="Item")  # noqa: F821

    storage = Storage()
    item1 = Item(
        {
            "id": 1,
            "items": [
                {
                    "id": 2,
                    "items": [
                        {
                            "id": 4,
                        }
                    ],
                },
                {
                    "id": 3,
                },
            ],
        },
        storage,
    )
    item2, item3 = item1.items
    item4 = storage.get(Item.id, 4)

    assert item1.id == 1
    assert item1.parent is None

    assert item2.id == 2
    assert item2.parent == item1
    assert item2.items == [item4]

    assert item3.id == 3
    assert item3.parent == item1
    assert item3.items == []


def test_set_value():
    class Address(Entity):
        street: str

    class User(Entity):
        id: int
        address: Address = Nested(entity_type=Address)

    storage = Storage()
    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "address": {
                "street": "kirova",
            },
        },
        storage=storage,
    )

    address = Address(data={"street": "lenina"}, storage=storage)
    john.address = address

    assert john.address is address
    assert john.dict() == {
        "id": 1,
        "name": "John",
        "description": "john smith",
        "address": {
            "street": "lenina",
        },
    }


def test_set_value_many():
    class Address(Entity):
        street: str

    class User(Entity):
        id: int
        addresses: t.List[Address] = Nested(entity_type=Address, many=True)

    storage = Storage()
    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "addresses": [
                {
                    "street": "kirova",
                }
            ],
        },
        storage=storage,
    )

    address = Address(data={"street": "lenina"}, storage=storage)
    john.addresses = [address]

    assert john.addresses == [address]
    assert john.dict() == {
        "id": 1,
        "name": "John",
        "description": "john smith",
        "addresses": [
            {
                "street": "lenina",
            }
        ],
    }


def test_set_value_with_back_relationship():
    class Address(Entity):
        street: str
        user: "User" = Relationship(entity_type="User")

    class User(Entity):
        id: int
        address: Address = Nested(
            entity_type=Address,
            back_relation=True,
        )

    storage = Storage()
    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "address": {
                "street": "kirova",
            },
        },
        storage=storage,
    )

    old_address = john.address

    assert old_address.user is john

    address = Address(data={"street": "lenina"}, storage=storage)
    john.address = address

    assert old_address.user is None
    assert address.user == john
    assert john.address is address
    assert john.dict() == {
        "id": 1,
        "name": "John",
        "description": "john smith",
        "address": {
            "street": "lenina",
        },
    }


def test_set_value_many_with_back_relationship():
    class Address(Entity):
        street: str
        user: "User" = Relationship(entity_type="User")

    class User(Entity):
        id: int
        addresses: t.List[Address] = Nested(
            entity_type=Address,
            back_relation=True,
            many=True,
        )

    storage = Storage()
    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "addresses": [
                {
                    "street": "kirova 1",
                },
                {
                    "street": "kirova 2",
                },
            ],
        },
        storage=storage,
    )

    old_address1, old_address2 = john.addresses

    address1 = Address(data={"street": "lenina 1"}, storage=storage)
    address2 = Address(data={"street": "lenina 2"}, storage=storage)
    john.addresses = [address1, address2]

    assert old_address1.user is None
    assert old_address2.user is None
    assert address1.user is john
    assert address2.user is john
    assert john.dict() == {
        "id": 1,
        "name": "John",
        "description": "john smith",
        "addresses": [
            {
                "street": "lenina 1",
            },
            {
                "street": "lenina 2",
            },
        ],
    }


def test_change_back_relationship_when_many():
    class Address(Entity):
        street: str
        user: "User" = Relationship(entity_type="User")

    class User(Entity):
        id: int
        addresses: t.List[Address] = Nested(
            entity_type=Address,
            back_relation=True,
            many=True,
        )

    storage = Storage()
    john = User(
        data={
            "id": 1,
            "name": "John",
            "description": "john smith",
            "addresses": [
                {
                    "street": "kirova 1",
                },
                {
                    "street": "kirova 2",
                },
            ],
        },
        storage=storage,
    )

    old_address1, old_address2 = john.addresses

    john.addresses.remove(old_address1)

    assert old_address1.user is None
    assert old_address2.user is john

    john.addresses.clear()

    assert old_address1.user is None
    assert old_address2.user is None
    assert john.addresses == []

    address1 = Address(data={"street": "lenina 1"}, storage=storage)
    address2 = Address(data={"street": "lenina 2"}, storage=storage)

    john.addresses.append(address1)

    assert address1.user is john
    assert john.addresses == [address1]

    john.addresses.extend([address2])

    assert address2.user is john
    assert john.addresses == [address1, address2]
    assert john.dict() == {
        "id": 1,
        "name": "John",
        "description": "john smith",
        "addresses": [
            {
                "street": "lenina 1",
            },
            {
                "street": "lenina 2",
            },
        ],
    }

    with pytest.raises(ValueError):
        john.addresses = None
