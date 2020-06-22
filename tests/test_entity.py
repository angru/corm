import pytest

from corm import Entity, Field, Storage


def test_base_entity():
    storage = Storage()

    class User(Entity):
        id: int
        name: str = Field(default='Bob')

    john = User(
        data={
            'id': 1,
            'name': 'John',
            'description': 'john smith',
        },
        storage=storage,
    )

    assert john.id == 1
    assert john.name == 'John'

    john.name = 'Not John'

    assert john.dict(strip_none=True) == {
        'id': 1,
        'name': 'Not John',
        'description': 'john smith',
    }


def test_same_pk():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    User({'id': 1}, storage)

    with pytest.raises(ValueError):
        User({'id': 1}, storage)


def multiple_primary_keys():
    class User(Entity):
        id: int = Field(pk=True)
        guid: str = Field(pk=True)
        name: str

    storage = Storage()
    user = User({'id': 1, 'guid': '1234', 'name': 'john'}, storage)

    assert storage.get(User.id, 1) == user
    assert storage.get(User.guid, '1234') == user
    assert storage.get(User.name, 'john') is None
