from corm import Entity, Field, KeyManager, KeyNested, Storage


class User(Entity):
    id: int = Field(pk=True)


class UserKeyManager(KeyManager):
    def get(self, data: dict[str, int]) -> int:
        return data["id"]

    def prepare_to_set(self, entity: Entity | None) -> dict[str, int] | None:
        if entity is None:
            return None
        assert isinstance(entity, User)
        return {"id": entity.id}


class Team(Entity):
    members: list[User] = KeyNested(
        User.id, origin="member_refs", key_manager=UserKeyManager()
    )


storage = Storage()
amina = User({"id": 123}, storage)
lee = User({"id": 456}, storage)
team = Team({"member_refs": [{"id": 123}]}, storage)

assert team.members == [amina]
assert team.dict() == {"member_refs": [{"id": 123}]}

team.members = [amina, lee]

assert team.members == [amina, lee]
assert team.dict() == {"member_refs": [{"id": 123}, {"id": 456}]}
