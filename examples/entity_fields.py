from corm import Storage, Entity, Field


class User(Entity):
    id: int = Field(origin='user_id')
    name: str
    description: str = Field(default='user')


storage = Storage()
user = User(data={'user_id': 33, 'name': 'John'}, storage=storage)

assert user.id == 33
assert user.description == 'user'
assert user.dict() == {'user_id': 33, 'name': 'John', 'description': 'user'}
