class CormError(Exception):
    """Base class for corm errors."""


class ConfigurationError(CormError, ValueError):
    """An entity field or relation is configured incorrectly."""


class MissingFieldError(CormError, ValueError):
    """A field has neither an input value nor a default."""


class ReadOnlyFieldError(CormError, ValueError):
    """An assignment is not allowed for a field."""


class DuplicateKeyError(CormError, ValueError):
    """A primary key is already registered in storage."""


class EntityNotFoundError(CormError, ValueError):
    """A required key does not resolve to a stored entity."""


class RelationError(CormError, ValueError):
    """An operation cannot be applied to a relation."""


class RegistryError(CormError, LookupError):
    """An entity name is unknown or ambiguous."""
