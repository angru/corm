from collections.abc import Iterable

from corm import Entity, Field, Nested, Storage


class User(Entity):
    name: str


class Directory(Entity):
    users: list[User] = Nested()


def first_named(users: Iterable[User], name: str) -> User | None:
    return next((user for user in users if user.name == name), None)


store = Storage()
directory = Directory({"users": [{"name": "Lee"}, {"name": "Lee"}]}, store)
other = User({"name": "Amina"}, store)

assert first_named(directory.users, "Lee") is directory.users[0]
assert first_named(directory.users, "Amina") is None
assert first_named([other, *directory.users], "Amina") is other


class Member(User):
    id: int = Field(pk=True)


member = Member({"id": 7, "name": "Amina"}, store)
assert store.get(Member.id, 7) is member
assert store.get(Member.id, 8) is None
