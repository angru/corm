from copy import deepcopy

import pytest

from experiments.nested_transforms import (
    Person,
    Storage,
    check,
    export_directory,
    load_directory,
)


def payload():
    return {
        "primary": {
            "personId": 1,
            "name": "A",
            "internal_note": "secret A",
            "extra": {"tags": [1]},
        },
        "people": [
            {"id": 2, "name": "B", "internal_note": "secret B", "extra": {"tags": [2]}},
            {"personId": 3, "name": "C", "internal_note": "secret C"},
        ],
        "department": {"personId": 99, "internal_note": "department note"},
        "contact_id": 3,
        "metadata": {"internal_note": "document note"},
    }


def test_nested_policy_and_reference():
    check()
    source = payload()
    original = deepcopy(source)
    store = Storage()
    directory = load_directory(source, store)
    full = deepcopy(directory.dict())
    response = export_directory(directory)
    assert source == original
    assert [directory.primary.id, *(person.id for person in directory.people)] == [
        1,
        2,
        3,
    ]
    assert store.get(Person.id, 1) is directory.primary
    assert store.get(Person.id, 3) is directory.contact is directory.people[1]
    assert response["contact_id"] == 3
    assert response["primary"] == {"id": 1, "name": "A", "extra": {"tags": [1]}}
    assert response["people"] == [
        {"id": 2, "name": "B", "extra": {"tags": [2]}},
        {"id": 3, "name": "C"},
    ]
    assert response["department"] == source["department"]
    assert response["metadata"] == source["metadata"]
    response["primary"]["extra"]["tags"].append(9)
    assert directory.dict() == full
    assert full["primary"]["internal_note"] == "secret A"
    assert [p["internal_note"] for p in full["people"]] == ["secret B", "secret C"]


@pytest.mark.parametrize("position", ["primary", "people"])
def test_transform_failure_precedes_store_mutation(position):
    store = Storage()
    existing = Person({"id": 50, "name": "Existing", "internal_note": "keep"}, store)
    source = payload()
    target = source["primary"] if position == "primary" else source["people"][-1]
    target["id"] = 42
    original = deepcopy(source)
    with pytest.raises(ValueError, match="Supply either personId or id"):
        load_directory(source, store)
    assert source == original
    assert store.get(Person.id, 50) is existing
    assert all(store.get(Person.id, key) is None for key in (1, 2, 3, 42))
    assert list(store.iter_entities(Person)) == [existing]
