import pytest

from corm import (
    AccessMode,
    ConfigurationError,
    CormError,
    DuplicateKeyError,
    Entity,
    EntityNotFoundError,
    Field,
    KeyNested,
    MissingFieldError,
    Nested,
    ReadOnlyFieldError,
    RelationError,
    Relationship,
    Storage,
)


def test_missing_field():
    class User(Entity):
        name: str

    with pytest.raises(MissingFieldError, match=r"name.*User") as exc:
        User({}, Storage())
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)


def test_read_only_field():
    class User(Entity):
        name: str = Field(mode=AccessMode.GET_LOAD)

    user = User({"name": "old"}, Storage())
    with pytest.raises(ReadOnlyFieldError, match=r"name.*User") as exc:
        user.name = "new"
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)
    assert user.name == "old"


def test_duplicate_key():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    User({"id": 1}, storage)
    with pytest.raises(DuplicateKeyError, match=r"User\.id.*1") as exc:
        User({"id": 1}, storage)
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)


@pytest.mark.parametrize("many", [False, True])
def test_required_entity_not_found(many):
    class Address(Entity):
        id: int = Field(pk=True)

    class User(Entity):
        address = KeyNested(Address.id, many=many, required=True)

    user = User({"address": [1] if many else 1}, Storage())
    with pytest.raises(
        EntityNotFoundError, match=r"User\.address.*Address\.id.*1"
    ) as exc:
        user.address
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)


def test_duplicate_and_missing_relation():
    class Address(Entity):
        pass

    class User(Entity):
        address: str = Field()

    storage = Storage()
    user = User({"address": "home"}, storage)
    address = Address({}, storage)
    storage.make_relation(user, address, User.address)
    with pytest.raises(RelationError, match=r"User\.address.*already exists") as exc:
        storage.make_relation(user, address, User.address)
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)

    storage.remove_relation(user, address, User.address)
    with pytest.raises(RelationError, match=r"User\.address.*does not exist") as exc:
        storage.remove_relation(user, address, User.address)
    assert isinstance(exc.value, ValueError)


@pytest.mark.parametrize("reassign", [False, True])
def test_remove_missing_item_from_unpaired_nested_list(reassign):
    class Address(Entity):
        pass

    class User(Entity):
        addresses = Nested(Address, many=True, default=list)

    storage = Storage()
    user = User({}, storage)
    address = Address({}, storage)
    if reassign:
        user.addresses = [Address({}, storage)]
    before = list(user.addresses)

    with pytest.raises(RelationError, match=r"User\.addresses.*does not exist") as exc:
        user.addresses.remove(address)
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)
    assert user.addresses == before


def test_duplicate_item_in_unpaired_relationship_list():
    class Address(Entity):
        pass

    class User(Entity):
        addresses = Relationship(Address, many=True)

    storage = Storage()
    user = User({}, storage)
    address = Address({}, storage)
    addresses = user.addresses
    addresses.append(address)

    with pytest.raises(RelationError, match=r"User\.addresses.*already exists"):
        addresses.append(address)
    assert addresses == user.addresses == [address]


def test_key_nested_requires_a_primary_key():
    class Address(Entity):
        id: int = Field()

    with pytest.raises(ConfigurationError, match=r"Address\.id.*primary key") as exc:
        KeyNested(Address.id)
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, ValueError)
