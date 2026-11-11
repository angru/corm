from corm import Entity, Field, KeyNested, Relationship, Storage


class User(Entity):
    id: int = Field(pk=True)
    addresses = Relationship("Address", many=True)


class Address(Entity):
    user = KeyNested(User.id, origin="user_id", back_relation=True, required=False)


storage = Storage()
old_address = Address({"user_id": 1}, storage)
new_address = Address({"user_id": 5}, storage)
user = User({"id": 1}, storage)
assert old_address.user is user
assert new_address.user is None

user.id = 5

assert storage.get(User.id, 1) is None
assert storage.get(User.id, 5) is user
assert old_address.user is None
assert old_address.dict() == {"user_id": 1}
assert new_address.user is user
assert new_address in user.addresses
