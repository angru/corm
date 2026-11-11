from typing import assert_type, reveal_type

from corm import AccessMode, Entity, Field, KeyNested, Nested, Relationship, Storage


class Address(Entity):
    id: int = Field(pk=True)
    residents: list["User"] = Relationship()


class User(Entity):
    id: int = Field(pk=True, mode=AccessMode.GET | AccessMode.SET | AccessMode.LOAD)
    address: Address = Nested()
    mailing_address: Address = KeyNested(Address.id, back_populates="residents")


def check_types(user: User, storage: Storage) -> None:
    reveal_type(user.address)
    reveal_type(user.id)
    assert_type(user.address, Address)
    assert_type(user.id, int)
    assert_type(user.mailing_address, Address)
    assert_type(user.mailing_address.residents, list[User])
    assert_type(storage.get(User.id, user.id), Entity | None)
