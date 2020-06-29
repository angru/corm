from corm import Entity, Field, Storage, RelationType


def test_add_by_primary_key():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    john = User(
        data={'id': 1},
        storage=storage,
    )

    assert storage.get(User.id, 1) == john


def test_make_relation():
    class User(Entity):
        id: int

    class Address(Entity):
        id: int

    storage = Storage()
    user = User(data={'id': 1}, storage=storage)
    address1 = Address(data={'id': 1}, storage=storage)
    address2 = Address(data={'id': 2}, storage=storage)

    storage.make_relation(
        from_=user,
        to_=address1,
        relation_type=RelationType.RELATED,
    )
    storage.make_relation(
        from_=user,
        to_=address2,
        relation_type=RelationType.CHILD,
    )

    assert storage.get_one_related_entity(
        user,
        Address,
        RelationType.RELATED,
    ) == address1
    assert storage.get_related_entities(
        user,
        Address,
        RelationType.RELATED,
    ) == [address1]


def test_remove_relation():
    class User(Entity):
        id: int

    class Address(Entity):
        id: int

    storage = Storage()
    user = User(data={'id': 1}, storage=storage)
    address1 = Address(data={'id': 1}, storage=storage)
    address2 = Address(data={'id': 2}, storage=storage)
    address3 = Address(data={'id': 3}, storage=storage)

    storage.make_relation(
        from_=user,
        to_=address1,
        relation_type=RelationType.RELATED,
    )
    storage.make_relation(
        from_=user,
        to_=address2,
        relation_type=RelationType.RELATED,
    )
    storage.make_relation(
        from_=user,
        to_=address3,
        relation_type=RelationType.PARENT,
    )

    assert storage.get_related_entities(
        user,
        Address,
        RelationType.RELATED,
    ) == [
        address1,
        address2,
    ]

    storage.remove_relation(user, address1, RelationType.RELATED)

    assert storage.get_related_entities(
        user,
        Address,
        RelationType.RELATED,
    ) == [address2]


def test_remove_relations():
    class User(Entity):
        id: int

    class Address(Entity):
        id: int

    storage = Storage()
    user = User(data={'id': 1}, storage=storage)
    address1 = Address(data={'id': 1}, storage=storage)
    address2 = Address(data={'id': 2}, storage=storage)
    address3 = Address(data={'id': 3}, storage=storage)

    storage.make_relation(
        from_=user,
        to_=address1,
        relation_type=RelationType.RELATED,
    )
    storage.make_relation(
        from_=user,
        to_=address2,
        relation_type=RelationType.RELATED,
    )
    storage.make_relation(
        from_=user,
        to_=address3,
        relation_type=RelationType.PARENT,
    )

    assert storage.get_related_entities(
        user,
        Address,
        RelationType.RELATED,
    ) == [
        address1,
        address2,
    ]

    storage.remove_relations(user, Address, RelationType.RELATED)

    assert storage.get_related_entities(
        user,
        Address,
        RelationType.RELATED,
    ) == []
    assert storage.get_related_entities(
        user,
        Address,
        RelationType.PARENT,
    ) == [address3]
