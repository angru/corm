import pytest

from corm import Entity, Field, RelationType, Storage


def test_add_by_primary_key():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    john = User(
        data={"id": 1},
        storage=storage,
    )

    assert storage.get(User.id, 1) == john


def test_make_relation():
    class User(Entity):
        id: int

    class Address(Entity):
        id: int

    storage = Storage()
    user = User(data={"id": 1}, storage=storage)
    address1 = Address(data={"id": 1}, storage=storage)
    address2 = Address(data={"id": 2}, storage=storage)

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

    assert (
        storage.get_one_related_entity(
            user,
            Address,
            RelationType.RELATED,
        )
        == address1
    )
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
    user = User(data={"id": 1}, storage=storage)
    address1 = Address(data={"id": 1}, storage=storage)
    address2 = Address(data={"id": 2}, storage=storage)
    address3 = Address(data={"id": 3}, storage=storage)

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
    user = User(data={"id": 1}, storage=storage)
    address1 = Address(data={"id": 1}, storage=storage)
    address2 = Address(data={"id": 2}, storage=storage)
    address3 = Address(data={"id": 3}, storage=storage)

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

    assert (
        storage.get_related_entities(
            user,
            Address,
            RelationType.RELATED,
        )
        == []
    )
    assert storage.get_related_entities(
        user,
        Address,
        RelationType.PARENT,
    ) == [address3]


def test_remove_subclass_relations_from_all_lookups():
    class Member(Entity):
        pass

    class Manager(Member):
        pass

    class Auditor(Entity):
        pass

    class Director(Manager, Auditor):
        pass

    class Contractor(Member):
        pass

    storage = Storage()
    team = Entity({}, storage)
    member = Member({}, storage)
    director = Director({}, storage)
    manager = Manager({}, storage)
    contractor = Contractor({}, storage)
    other_director = Director({}, storage)
    related = RelationType.RELATED
    for entity in (member, director, manager, contractor, other_director):
        storage.make_relation(team, entity, related)
    storage.make_relation(team, other_director, RelationType.PARENT)

    with pytest.raises(ValueError, match="already exists"):
        storage.make_relation(team, director, related)

    assert storage.get_related_entities(team, Entity, related) == [
        member,
        director,
        manager,
        contractor,
        other_director,
    ]
    assert storage.get_related_entities(team, Manager, related) == [
        director,
        manager,
        other_director,
    ]
    storage.remove_relation(team, director, related)
    assert storage.get_related_entities(team, Member, related) == [
        member,
        manager,
        contractor,
        other_director,
    ]
    assert storage.get_related_entities(team, Manager, related) == [
        manager,
        other_director,
    ]
    assert storage.get_one_related_entity(team, Director, related) is other_director
    assert storage.get_related_entities(team, Auditor, related) == [other_director]

    storage.remove_relations(team, Manager, related)
    assert storage.get_related_entities(team, Member, related) == [member, contractor]
    assert storage.get_related_entities(team, Manager, related) == []
    assert storage.get_related_entities(team, Director, related) == []
    assert storage.get_related_entities(team, Auditor, related) == []
    assert storage.get_related_entities(team, Director, RelationType.PARENT) == [
        other_director,
    ]

    storage.remove_relations(team, Member, related)
    assert storage.get_related_entities(team, Contractor, related) == []
    assert storage.get_related_entities(team, Entity, related) == []


def test_equal_targets_of_different_classes_are_distinct_relations():
    class Member(Entity):
        def __eq__(self, other):
            return isinstance(other, Member)

    class Manager(Member):
        pass

    storage = Storage()
    team = Entity({}, storage)
    manager = Manager({}, storage)
    member = Member({}, storage)
    related = RelationType.RELATED
    storage.make_relation(team, manager, related)
    storage.make_relation(team, member, related)

    storage.remove_relation(team, member, related)
    (remaining,) = storage.get_related_entities(team, Member, related)
    assert remaining is manager
    assert storage.get_one_related_entity(team, Manager, related) is manager
