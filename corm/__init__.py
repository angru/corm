from typing import TYPE_CHECKING, Any

from corm.constants import AccessMode, RelationType
from corm.entity import Entity
from corm.exceptions import (
    ConfigurationError,
    CormError,
    DuplicateKeyError,
    EntityNotFoundError,
    MissingFieldError,
    ReadOnlyFieldError,
    RegistryError,
    RelationError,
)
from corm.fields import KeyManager
from corm.storage import Storage

if TYPE_CHECKING:
    from collections.abc import Hashable

    # EntityMeta installs the runtime descriptors. Annotated instance reads
    # retain the declared type, independent of the descriptor constructor.
    def Field(
        pk: bool = False,
        mode: AccessMode = AccessMode.ALL,
        default: Any = ...,
        origin: str | None = None,
        destination: str | None = None,
    ) -> Any: ...

    def Nested(
        entity_type: str | type[Entity] | None = None,
        many: bool | None = None,
        back_relation: Hashable = False,
        mode: AccessMode = AccessMode.ALL,
        default: Any = ...,
        origin: str | None = None,
        destination: str | None = None,
        *,
        back_populates: str | None = None,
    ) -> Any: ...

    def Relationship(
        entity_type: str | type[Entity] | None = None,
        relation_type: Hashable = RelationType.RELATED,
        many: bool | None = None,
    ) -> Any: ...

    def KeyNested(
        related_entity_field: object,
        back_relation: Hashable = False,
        many: bool | None = None,
        mode: AccessMode = AccessMode.GET_SET_LOAD,
        default: Any = ...,
        origin: str | None = None,
        destination: str | None = None,
        key_manager: KeyManager | None = None,
        required: bool = True,
        *,
        back_populates: str | None = None,
    ) -> Any: ...
else:
    from corm.fields import Field, KeyNested, Nested, Relationship

# Preserve the existing export order.
__all__ = (  # noqa: RUF022
    "Entity",
    "Field",
    "Nested",
    "Relationship",
    "KeyNested",
    "KeyManager",
    "Storage",
    "RelationType",
    "AccessMode",
    "CormError",
    "ConfigurationError",
    "MissingFieldError",
    "ReadOnlyFieldError",
    "DuplicateKeyError",
    "EntityNotFoundError",
    "RelationError",
    "RegistryError",
)
