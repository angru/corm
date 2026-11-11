from __future__ import annotations

import typing

import pytest

from corm import Entity, Nested, Relationship, Storage, registry


def test_infer_from_postponed_annotations():
    class User(Entity):
        addresses: typing.Optional[list[Address]] = Nested()  # noqa: UP045
        manager: "User | None" = Nested(default=None)  # noqa: UP037
        contacts: typing.List["Address"] = Relationship()  # noqa: UP006, UP037
        primary: models.Primary = Relationship()  # noqa: F821

    with pytest.raises(KeyError, match=r"User\.contacts.*Unknown entity 'Address'"):
        User.contacts.entity_type

    class Address(Entity):
        pass

    class Primary(Entity):
        pass

    registry.add(Primary, name="models.Primary")
    user = User({"addresses": [{}]}, Storage())
    user.contacts = user.addresses
    primary = Primary({}, user.storage)
    user.primary = primary

    assert User.addresses.entity_type is Address
    assert User.manager.entity_type is User
    assert user.manager is None
    assert user.contacts == user.addresses
    assert user.primary is primary
