import sys
import typing

import pytest

from corm import Entity, Field, KeyNested, Nested, Relationship, Storage


@pytest.mark.parametrize("field_type", [Nested, Relationship])
@pytest.mark.parametrize(
    ("annotate", "many"),
    [
        pytest.param(lambda address: address, False, id="entity"),
        pytest.param(lambda address: "Address", False, id="forward"),
        pytest.param(
            lambda address: typing.Optional[address],  # noqa: UP045
            False,
            id="optional",
        ),
        pytest.param(lambda address: address | None, False, id="union"),
        pytest.param(lambda address: list[address], True, id="list"),
        pytest.param(
            lambda address: typing.List[address],  # noqa: UP006
            True,
            id="typing-list",
        ),
        pytest.param(lambda address: list[address.__name__], True, id="forward-list"),
        pytest.param(
            lambda address: typing.List[address.__name__],  # noqa: UP006
            True,
            id="typing-forward-list",
        ),
        pytest.param(
            lambda address: typing.Optional[list[address]],  # noqa: UP045
            True,
            id="optional-list",
        ),
    ],
)
def test_infer_entity_type_and_many(field_type, annotate, many):
    class Address(Entity):
        street: str

    annotation = annotate(Address)

    class User(Entity):
        address: annotation = field_type()

    assert User.address.entity_type is Address
    assert User.address.many is many

    storage = Storage()
    data = {"street": "Main"}
    if field_type is Nested:
        user = User({"address": [data] if many else data}, storage)
        assert user.dict() == {"address": [data] if many else data}
    else:
        user = User({}, storage)
        address = Address(data, storage)
        user.address = [address] if many else address

    related = user.address[0] if many else user.address
    assert isinstance(related, Address)
    assert related.street == "Main"


def test_infer_self_reference():
    class Node(Entity):
        parent: "Node | None" = Nested(default=None)
        children: list["Node"] = Nested(default=list)

    root = Node({"children": [{"parent": {}}]}, Storage())

    assert root.parent is None
    assert isinstance(root.children[0], Node)
    assert isinstance(root.children[0].parent, Node)


@pytest.mark.skipif(sys.version_info < (3, 14), reason="requires deferred annotations")
def test_infer_from_deferred_forward_refs():
    class User(Entity):
        address: Address | None = Nested()  # noqa: F821
        addresses: list[Address] = Relationship()  # noqa: F821

    with pytest.raises(KeyError, match=r"User\.address.*Unknown entity 'Address'"):
        User.address.entity_type

    class Address(Entity):
        pass

    user = User({"address": {}}, Storage())
    user.addresses = [user.address]

    assert isinstance(user.address, Address)
    assert user.addresses == [user.address]


@pytest.mark.parametrize("field_type", [Nested, Relationship])
def test_explicit_options_override_annotation_independently(field_type):
    class Address(Entity):
        pass

    class Other(Entity):
        pass

    class User(Entity):
        explicit_type: list[Address] = field_type(entity_type=Other)
        explicit_single: list[Address] = field_type(many=False)
        explicit_many: Address = field_type(many=True)
        explicit_both: dict[str, Address] = field_type(entity_type=Other, many=True)

    assert User.explicit_type.entity_type is Other
    assert User.explicit_type.many is True
    assert User.explicit_single.entity_type is Address
    assert User.explicit_single.many is False
    assert User.explicit_many.entity_type is Address
    assert User.explicit_many.many is True
    assert User.explicit_both.entity_type is Other
    assert User.explicit_both.many is True


def test_key_nested_infers_many_and_uses_the_explicit_key_field():
    class Address(Entity):
        id: int = Field(pk=True)

    class User(Entity):
        addresses: "list[Unregistered] | None" = KeyNested(Address.id)  # noqa: F821
        address: list[Address] = KeyNested(Address.id, many=False)
        legacy = KeyNested(Address.id)

    storage = Storage()
    address = Address({"id": 1}, storage)
    user = User({"addresses": [1], "address": 1, "legacy": 1}, storage)

    assert User.addresses.many is True
    assert User.address.many is False
    assert User.legacy.many is False
    assert user.addresses == [address]
    assert user.address is user.legacy is address


@pytest.mark.parametrize("field_type", [Nested, Relationship])
def test_inherited_field_keeps_its_inferred_configuration(field_type):
    class Base(Entity):
        related: "list[Base]" = field_type()

    class Child(Base):
        related: "Child"

    assert Base.related is Child.related
    assert Child.related.entity_type is Base
    assert Child.related.many is True


@pytest.mark.parametrize("field_type", [Nested, Relationship])
def test_missing_annotation_and_entity_type(field_type):
    with pytest.raises(ValueError, match=r"User\.address.*entity_type or annotation"):

        class User(Entity):
            address = field_type()


@pytest.mark.parametrize("field_type", [Nested, Relationship])
@pytest.mark.parametrize(
    "annotate",
    [
        lambda address, other: dict[str, address],
        lambda address, other: address | other,
        lambda address, other: int,
        lambda address, other: list[dict[str, address]],
        lambda address, other: "dict[str, Address]",
        lambda address, other: "Address | Other",
        lambda address, other: "get_entity_type()",
        lambda address, other: "list[Address",
    ],
)
def test_unsupported_annotation(field_type, annotate):
    class Address(Entity):
        pass

    class Other(Entity):
        pass

    annotation = annotate(Address, Other)

    with pytest.raises(
        ValueError, match=r"Unsupported relation annotation.*User\.address"
    ):

        class User(Entity):
            address: annotation = field_type()
