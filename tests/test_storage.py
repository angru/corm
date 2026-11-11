import pytest

from corm import Entity, Field, Relationship, RelationType, Storage


def test_add_by_primary_key():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    john = User(
        data={"id": 1},
        storage=storage,
    )

    assert storage.get(User.id, 1) == john


def test_change_primary_key():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    user = User({"id": 1}, storage)
    user.id = 5
    user.id = 5

    assert user.id == 5
    assert storage.get(User.id, 5) is user
    assert storage.get(User.id, 1) is None


def test_primary_key_conflict_leaves_storage_and_data_unchanged():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    user = User({"id": 1}, storage)
    other = User({"id": 5}, storage)

    with pytest.raises(ValueError) as insert_error:
        User({"id": 5}, storage)
    with pytest.raises(ValueError) as assignment_error:
        user.id = 5

    assert str(assignment_error.value) == str(insert_error.value)
    assert user.id == 1
    assert other.id == 5
    assert storage.get(User.id, 1) is user
    assert storage.get(User.id, 5) is other


def test_change_one_of_two_primary_keys():
    class User(Entity):
        id: int = Field(pk=True, origin="user_id")
        username: str = Field(pk=True)

    storage = Storage()
    user = User({"user_id": 1, "username": "john"}, storage)
    user.id = 5

    assert user.dict() == {"user_id": 5, "username": "john"}
    assert storage.get(User.id, 1) is None
    assert storage.get(User.id, 5) is user
    assert storage.get(User.username, "john") is user


def test_read_missing_relation_does_not_modify_storage():
    class User(Entity):
        pass

    class Address(Entity):
        street: str
        user = Relationship(entity_type="User")
        users = Relationship(entity_type="User", many=True)

    storage = Storage()
    address = Address({"street": "x"}, storage)
    assert address.user is None
    assert address.users == []
    assert not storage._relations

    user = User({}, storage)
    storage.make_relation(address, user, RelationType.CHILD)
    before = set(storage._relations[address])
    assert address.user is None
    assert address.users == []
    assert set(storage._relations[address]) == before


def test_get_related_entities_returns_a_new_list():
    storage = Storage()
    source = Entity({}, storage)
    target = Entity({}, storage)
    related = RelationType.RELATED
    storage.make_relation(source, target, related)

    result = storage.get_related_entities(source, Entity, related)
    assert result == [target]
    assert result is not storage.get_related_entities(source, Entity, related)
    result.clear()
    assert storage.get_related_entities(source, Entity, related) == [target]


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

    storage.make_relation(user, address1, RelationType.RELATED)
    with pytest.raises(ValueError, match="already exists"):
        storage.make_relation(user, address2, RelationType.RELATED)

    assert storage.get_related_entities(user, Address, RelationType.RELATED) == [
        address2,
        address1,
    ]


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


@pytest.mark.parametrize("hashable", [False, True])
def test_equal_targets_of_different_classes_are_distinct_relations(hashable):
    class Member(Entity):
        __hash__ = (lambda self: 0) if hashable else None

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

    equal_member = Member({}, storage)
    with pytest.raises(ValueError, match="already exists"):
        storage.make_relation(team, equal_member, related)

    storage.remove_relation(team, equal_member, related)
    (remaining,) = storage.get_related_entities(team, Member, related)
    assert remaining is manager
    assert storage.get_one_related_entity(team, Manager, related) is manager
