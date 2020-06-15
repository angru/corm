import pytest

from corm import registry


@pytest.fixture(autouse=True)
def clear_registry():
    registry.clear()
