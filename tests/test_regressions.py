import sys

import pytest

from corm import (
    CormError,
    Entity,
    Field,
    KeyNested,
    Nested,
    RegistryError,
    Relationship,
    Storage,
    registry,
)


def test_annotation_only_forward_reference():
    class Item(Entity):
        value: "NotDefined"  # noqa: F821

    item = Item({"value": 42}, Storage())
    assert item.value == 42


@pytest.mark.skipif(sys.version_info < (3, 14), reason="Deferred annotations need 3.14")
def test_deferred_undefined_annotation():
    namespace = {"Entity": Entity, "__name__": __name__}
    exec("class Item(Entity):\n    value: NotDefined", namespace)
    item = namespace["Item"]({"value": 42}, Storage())
    assert item.value == 42


def test_dict_preserves_nested_entities_and_unknown_keys():
    class Address(Entity):
        street: str

    class User(Entity):
        address = Nested(entity_type=Address)
        addresses = Nested(entity_type=Address, many=True)

    user = User(
        {"address": {"street": "x"}, "addresses": [{"street": "y"}], "extra": 7},
        Storage(),
    )
    address = user.address
    addresses = user.addresses
    result = user.dict()
    assert result == {
        "address": {"street": "x"},
        "addresses": [{"street": "y"}],
        "extra": 7,
    }
    assert result is not user._data
    assert user.dict() == result
    assert user.address is address
    assert user.addresses is addresses
    assert isinstance(user.addresses[0], Address)
    result["extra"] = 8
    result["address"]["street"] = "changed"
    assert user._data["extra"] == 7
    assert address.street == "x"


def test_dict_preserves_renamed_fields():
    class Data(Entity):
        foo = Field(origin="f", destination="g")
        optional = Field(origin="o", destination="p", default=None)

    data = Data({"f": 1}, Storage())
    assert data.dict() == {"g": 1, "p": None}
    assert data.dict() == {"g": 1, "p": None}
    assert data.foo == 1
    assert data.dict(strip_none=True) == {"g": 1}
    assert data._data == {"f": 1, "o": None}


def test_dict_nested_none():
    class Address(Entity):
        street: str

    class User(Entity):
        address = Nested(entity_type=Address)

    user = User({"address": {"street": "x"}}, Storage())
    user.address = None
    assert user.dict() == {"address": None}
    assert user.dict(strip_none=True) == {}
    assert user.address is None


def test_registry_replaces_same_full_name():
    first = type("User", (Entity,), {"__module__": "pkg.users"})
    second = type("User", (Entity,), {"__module__": "pkg.users"})
    assert first is not second
    assert registry.get("User") is second
    assert registry.get("pkg.users.User") is second


def test_registry_short_name_ambiguity_and_full_names():
    first = type("User", (Entity,), {"__module__": "pkg.first"})
    second = type("User", (Entity,), {"__module__": "pkg.second"})
    assert registry.get("pkg.first.User") is first
    assert registry.get("pkg.second.User") is second
    with pytest.raises(RegistryError) as exc:
        registry.get("User")
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, LookupError)
    assert "pkg.first.User" in str(exc.value)
    assert "pkg.second.User" in str(exc.value)


def test_registry_uses_qualnames():
    class First:
        class User(Entity):
            pass

    class Second:
        class User(Entity):
            pass

    for user in (First.User, Second.User):
        assert registry.get(f"{user.__module__}.{user.__qualname__}") is user
    with pytest.raises(RegistryError):
        registry.get("User")


def test_registry_unknown_name():
    with pytest.raises(RegistryError, match=r"Unknown entity.*MissingUser") as exc:
        registry.get("MissingUser")
    assert isinstance(exc.value, CormError)
    assert isinstance(exc.value, LookupError)


def test_entity_classmethod_and_staticmethod():
    class Data(Entity):
        x: int

        @classmethod
        def make(cls):
            return cls({"x": 1}, Storage())

        @staticmethod
        def answer():
            return 42

    data = Data.make()
    assert data.x == 1
    assert Data.answer() == data.answer() == 42
    assert set(Data.__fields__) == {"x"}


def test_nested_load_none_has_no_relations():
    class Address(Entity):
        street: str

    class User(Entity):
        address = Nested(entity_type=Address, back_relation=True)

    storage = Storage()
    user = User({"address": None}, storage)
    assert user.address is None
    assert not storage._entities
    assert not storage._relations


def test_nested_set_none_then_new_value():
    class Address(Entity):
        street: str
        user = Relationship(entity_type="User")

    class User(Entity):
        address = Nested(entity_type=Address, back_relation=True)

    storage = Storage()
    user = User({"address": {"street": "x"}}, storage)
    previous = user.address
    user.address = None
    assert previous.user is None
    user.address = None
    replacement = Address({"street": "z"}, storage)
    user.address = replacement
    assert user.address is replacement
    assert replacement.user is user
    assert previous.user is None
    assert None not in storage._relations


def test_nested_without_back_relation_does_not_create_relation():
    class Address(Entity):
        street: str

    class User(Entity):
        address = Nested(entity_type=Address)

    storage = Storage()
    user = User({"address": {"street": "x"}}, storage)
    user.address = Address({"street": "y"}, storage)
    assert not storage._relations


@pytest.mark.parametrize("back_relation", [False, True])
def test_nested_many_assign_itself(back_relation):
    class Child(Entity):
        v: int
        parent = Relationship(entity_type="Parent")

    class Parent(Entity):
        children = Nested(entity_type=Child, many=True, back_relation=back_relation)

    parent = Parent({"children": [{"v": 1}, {"v": 2}]}, Storage())
    children = list(parent.children)
    parent.children = parent.children
    assert parent.children == children
    assert [child.v for child in parent.children] == [1, 2]
    if back_relation:
        assert all(child.parent is parent for child in children)


def test_nested_many_assign_slice_preserves_back_relations():
    class Child(Entity):
        v: int
        parent = Relationship(entity_type="Parent")

    class Parent(Entity):
        children = Nested(entity_type=Child, many=True, back_relation=True)

    parent = Parent({"children": [{"v": 1}, {"v": 2}]}, Storage())
    kept, dropped = parent.children
    parent.children = parent.children[:1]
    assert parent.children == [kept]
    assert kept.parent is parent
    assert dropped.parent is None


def test_failed_entity_load_is_not_registered():
    class User(Entity):
        id = Field(pk=True)
        name: str

    storage = Storage()
    with pytest.raises(ValueError, match="No value for field 'id'"):
        User({}, storage)
    assert storage.get(User.id, None) is None
    with pytest.raises(ValueError, match="No value for field 'name'"):
        User({"id": 1}, storage)
    assert storage.get(User.id, 1) is None
    assert not storage._entities


def test_primary_key_default_used_for_storage():
    class User(Entity):
        id = Field(pk=True, default=42)

    storage = Storage()
    user = User({}, storage)
    assert user.id == 42
    assert storage.get(User.id, 42) is user
    assert storage.get(User.id, None) is None


@pytest.mark.parametrize("use_default", [False, True])
def test_duplicate_primary_key_does_not_store_nested_child(use_default):
    class Address(Entity):
        id = Field(pk=True)

    class User(Entity):
        address = Nested(entity_type=Address)
        id = Field(pk=True, origin="user_id", default=1)

    storage = Storage()
    original = User({"user_id": 1, "address": {"id": 5}}, storage)
    duplicate_data = {"address": {"id": 6}}
    if not use_default:
        duplicate_data["user_id"] = 1

    with pytest.raises(ValueError, match=r"User.id.*=1 already in storage"):
        User(duplicate_data, storage)

    assert storage.get(User.id, 1) is original
    assert storage.get(Address.id, 6) is None
    retried = User({"user_id": 2, "address": {"id": 6}}, storage)
    assert storage.get(Address.id, 6) is retried.address


@pytest.mark.parametrize("target_exists", [True, False])
def test_duplicate_primary_key_does_not_add_key_nested_relation(target_exists):
    default_calls = []

    def default_id():
        default_calls.append(10)
        return 10

    class Target(Entity):
        id = Field(pk=True)
        holders = Relationship(entity_type="Holder", many=True)

    class Holder(Entity):
        target = KeyNested(Target.id, back_relation=True)
        id = Field(pk=True, default=default_id)

    storage = Storage()
    if target_exists:
        target = Target({"id": 1}, storage)
    original = Holder({"target": 1}, storage)

    with pytest.raises(ValueError, match=r"Holder.id.*=10 already in storage"):
        Holder({"target": 1}, storage)

    if not target_exists:
        target = Target({"id": 1}, storage)
    assert target.holders == [original]
    assert original.target is target
    assert storage.get(Holder.id, 10) is original
    assert default_calls == [10, 10]


def test_annotation_only_field_with_future_annotations():
    namespace = {"Entity": Entity, "__name__": __name__}
    exec(
        "from __future__ import annotations\n"
        "class Item(Entity):\n"
        "    value: NotDefined",
        namespace,
    )
    item = namespace["Item"]({"value": 42}, Storage())
    assert item.value == 42


def test_annotation_only_field_in_dynamic_class():
    item_class = type(
        "Item", (Entity,), {"__module__": __name__, "__annotations__": {"value": int}}
    )
    assert item_class({"value": 42}, Storage()).value == 42
