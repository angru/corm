"""A document-boundary policy for one type at two known Nested paths."""

from copy import deepcopy
from typing import Any

from corm import Entity, Field, KeyNested, Nested, Storage


class Person(Entity):
    id: int = Field(pk=True)
    name: str
    internal_note: str


class Department(Entity):
    internal_note: str


class Directory(Entity):
    primary: Person = Nested()
    people: list[Person] = Nested()
    department: Department = Nested()
    contact: Person = KeyNested(Person.id, origin="contact_id")


def normalize_person(data: dict[str, Any]) -> None:
    if "personId" in data:
        if "id" in data:
            raise ValueError("Supply either personId or id")
        data["id"] = data.pop("personId")


def redact_person(data: dict[str, Any]) -> None:
    data.pop("internal_note", None)


def person_positions(data: dict[str, Any]) -> list[dict[str, Any]]:
    # Schema registrations: the scalar primary and every element of people.
    return [data["primary"], *data["people"]]


def load_directory(payload: dict[str, Any], storage: Storage) -> Directory:
    data = deepcopy(payload)
    for person in person_positions(data):
        normalize_person(person)
    return Directory(data, storage)


def export_directory(directory: Directory) -> dict[str, Any]:
    # Copy unknown values too: dict() need not deep-copy undeclared metadata.
    data = deepcopy(directory.dict())
    for person in person_positions(data):
        redact_person(person)
    return data


def check() -> None:
    payload = {
        "primary": {"personId": 1, "name": "A", "internal_note": "private A"},
        "people": [{"personId": 2, "name": "B", "internal_note": "private B"}],
        "department": {"internal_note": "public department note"},
        "contact_id": 2,
    }
    original = deepcopy(payload)
    directory = load_directory(payload, Storage())
    assert directory.contact is directory.people[0]
    assert directory.storage.get(Person.id, 1) is directory.primary
    assert directory.storage.get(Person.id, 2) is directory.contact
    response = export_directory(directory)
    assert response["primary"] == {"id": 1, "name": "A"}
    assert response["people"] == [{"id": 2, "name": "B"}]
    assert response["department"] == original["department"]
    assert directory.primary.internal_note == "private A"
    assert directory.people[0].internal_note == "private B"
    assert payload == original


if __name__ == "__main__":
    check()
