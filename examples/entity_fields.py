from corm import AccessMode, Entity, Field, ReadOnlyFieldError, Storage


class User(Entity):
    id: int = Field(origin="user_id", destination="id")
    name: str = Field(mode=AccessMode.GET | AccessMode.LOAD | AccessMode.DUMP)
    description: str = "Project member"
    nickname: str | None = Field(default=None)


payload = {"user_id": 33, "name": "Amina", "timezone": "UTC", "metadata": None}
user = User(payload, Storage())

assert user.id == 33
user.id = 34
assert payload["user_id"] == 34
assert user.name == "Amina"

try:
    user.name = "Mina"
except ReadOnlyFieldError:
    pass
else:
    raise AssertionError("The name field is read-only")

assert user.dict() == {
    "id": 34,
    "name": "Amina",
    "description": "Project member",
    "nickname": None,
    "timezone": "UTC",
    "metadata": None,
}
assert user.dict(strip_none=True) == {
    "id": 34,
    "name": "Amina",
    "description": "Project member",
    "timezone": "UTC",
    "metadata": None,
}
