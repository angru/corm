from corm import Model, Field, Storage


def test_add_by_primary_key():
    class User(Model):
        id: int = Field(pk=True)

    storage = Storage()
    john = User(
        data={'id': 1},
        storage=storage,
    )

    assert storage.get(User.id, 1) == john
