from corm import Entity, Field, KeyNested, Nested, Storage


class User(Entity):
    id: int = Field(pk=True)


class Membership(Entity):
    user: User | None = KeyNested(User.id, origin="entity_id", required=False)
    rank: int


class Team(Entity):
    members: list[Membership] = Nested()


storage = Storage()
amina = User({"id": 1}, storage)
lee = User({"id": 2}, storage)
team = Team(
    {
        "members": [
            {"entity_id": 1, "rank": 10},
            {"entity_id": 9, "rank": 90},
            {"entity_id": 1, "rank": 11},
        ]
    },
    storage,
)
first, pending, second = team.members
assert first.user is second.user is amina
assert pending.user is None

new_member = Membership({"entity_id": 2, "rank": 20}, storage)
team.members = [second, new_member, pending]
assert team.dict() == {
    "members": [
        {"entity_id": 1, "rank": 11},
        {"entity_id": 2, "rank": 20},
        {"entity_id": 9, "rank": 90},
    ]
}
assert new_member.user is lee
late_user = User({"id": 9}, storage)
assert pending.user is late_user
