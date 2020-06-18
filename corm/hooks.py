import typing as t

if t.TYPE_CHECKING:
    from corm.entity import Entity


class Hook:
    match_entities: t.List['Entity']

    def go(self, data, entity: 'Entity'):
        raise NotImplementedError