"""Explore ordering when enumerating Storage's primary-key index.

Run with ``python -m experiments.entity_enumeration``.
"""

from collections.abc import Callable
from typing import TypeVar

from corm import Entity, Field, Nested, Storage

EntityT = TypeVar("EntityT", bound=Entity)


def ordered_entities(
    store: Storage, entity_type: type[EntityT], key: Callable[[EntityT], str]
) -> list[EntityT]:
    """Sort the snapshot by a caller-supplied, stable, unique key."""
    return sorted(store.iter_entities(entity_type), key=key)


class Person(Entity):
    name: str


class Member(Person):
    id: int = Field(pk=True)


class Contact(Person):
    id: int = Field(pk=True)
    alias: int = Field(pk=True)


class Directory(Entity):
    members: list[Member] = Nested()
    contacts: list[Contact] = Nested()


def main() -> None:
    store = Storage()
    root = Directory(
        {
            "members": [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
            "contacts": [{"id": 3, "alias": 30, "name": "C"}],
        },
        store,
    )
    a, b = root.members
    (c,) = root.contacts
    unkeyed = Person({"name": "unkeyed"}, store)
    other = Member({"id": 1, "name": "other store"}, Storage())

    def index_order() -> list[Person]:
        return list(store.iter_entities(Person))

    def stable_order() -> list[Person]:
        return ordered_entities(store, Person, key=lambda person: person.name)

    assert index_order() == [a, b, c]
    assert list(store.iter_entities(Contact)) == [c]
    assert unkeyed not in index_order() and other not in index_order()
    assert stable_order() == [a, b, c]

    store.rekey(root, a, Member.id, 10)
    assert index_order() == [b, c, a]
    assert stable_order() == [a, b, c]
    store.rekey(root, c, Contact.id, 11)
    assert index_order() == [b, c, a]  # C's alias entry still precedes A.
    assert stable_order() == [a, b, c]
    assert store.get(Contact.alias, 30) is c and store.get(Contact.id, 11) is c
    store.rekey(root, c, Contact.alias, 31)
    assert index_order() == [b, a, c]  # Neither of C's original entries remains.
    assert stable_order() == [a, b, c]
    assert store.get(Contact.alias, 31) is c and store.get(Contact.id, 11) is c
    print("Index order after rekeys:", [person.name for person in index_order()])
    print("Caller order after rekeys:", [person.name for person in stable_order()])


if __name__ == "__main__":
    main()
