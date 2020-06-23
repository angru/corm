import pytest

from corm import Entity, Field, Storage, AccessMode


def test_base_entity():
    class User(Entity):
        id: int
        name: str = Field(default='Bob')
        description: str = 'some text'

    storage = Storage()
    john = User(
        data={
            'id': 1,
            'name': 'John',
            'address': 'First st. 1',
        },
        storage=storage,
    )

    assert john.id == 1
    assert john.name == 'John'
    assert john.description == 'some text'

    john.name = 'Not John'

    assert john.dict(strip_none=True) == {
        'id': 1,
        'name': 'Not John',
        'description': 'some text',
        'address': 'First st. 1',
    }


def test_origin_destination_setting():
    class Data(Entity):
        attr1 = Field(origin='_attr1', destination='attr1_')
        attr2 = Field(origin='_attr2')
        attr3 = Field(destination='attr3_')

    storage = Storage()
    data = Data(
        data={
            '_attr1': 1,
            '_attr2': 2,
            'attr3': 3,
        },
        storage=storage,
    )

    assert data.attr1 == 1
    assert data.attr2 == 2
    assert data.attr3 == 3
    assert data.dict() == {
        'attr1_': 1,
        '_attr2': 2,
        'attr3_': 3,
    }


def test_same_pk():
    class User(Entity):
        id: int = Field(pk=True)

    storage = Storage()
    User({'id': 1}, storage)

    with pytest.raises(ValueError):
        User({'id': 1}, storage)


def test_multiple_primary_keys():
    class User(Entity):
        id: int = Field(pk=True)
        guid: str = Field(pk=True)
        name: str

    storage = Storage()
    user = User({'id': 1, 'guid': '1234', 'name': 'john'}, storage)

    assert storage.get(User.id, 1) == user
    assert storage.get(User.guid, '1234') == user
    assert storage.get(User.name, 'john') is None


def test_change_field_value():
    class User(Entity):
        id: int = Field(pk=True, mode=AccessMode.GET_LOAD_DUMP)
        guid: str = Field(pk=True)
        name: str = Field(mode=AccessMode.GET_LOAD_DUMP)
        description: str

    storage = Storage()
    user = User(
        {
            'id': 1,
            'guid': '1234',
            'name': 'john',
            'description': '',
        },
        storage,
    )

    with pytest.raises(ValueError):
        user.id = 2

    with pytest.raises(ValueError):
        user.name = 'Bob'

    user.guid = '4321'
    user.description = 'cool guy'

    assert user.dict() == {
        'id': 1,
        'guid': '4321',
        'name': 'john',
        'description': 'cool guy',
    }
