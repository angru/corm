from collections.abc import Callable
from copy import deepcopy
from typing import Any

from corm import Entity, Field, Nested, Storage


class Profile(Entity):
    name: str
    internal_note: str


class Member(Entity):
    id: int = Field(pk=True)
    profile: Profile = Nested()


def load_member(payload: dict[str, Any], storage: Storage) -> Member:
    data = deepcopy(payload)
    if "memberId" in data:
        if "id" in data:
            raise ValueError("Supply either memberId or id")
        data["id"] = data.pop("memberId")
    return Member(data, storage)


def export_member(member: Member) -> dict[str, Any]:
    data = member.dict()
    del data["profile"]["internal_note"]
    return data


def check_transforms(
    load: Callable[[dict[str, Any]], Member],
    export: Callable[[Member], dict[str, Any]],
) -> None:
    payload = {
        "memberId": 7,
        "profile": {"name": "Amina", "internal_note": "Confirm spelling"},
    }
    original = deepcopy(payload)
    member = load(payload)
    assert member.storage.get(Member.id, 7) is member
    assert export(member) == {"id": 7, "profile": {"name": "Amina"}}
    assert member.profile.internal_note == "Confirm spelling"
    assert member.dict() == {"id": 7, "profile": original["profile"]}
    assert payload == original

    canonical = {"id": 8, "profile": original["profile"]}
    assert load(canonical).id == 8
    try:
        load({**canonical, "memberId": 7})
    except ValueError as exc:
        assert str(exc) == "Supply either memberId or id"
    else:
        raise AssertionError("Ambiguous IDs must be rejected")


if __name__ == "__main__":
    check_transforms(lambda payload: load_member(payload, Storage()), export_member)
