import typing as t

if t.TYPE_CHECKING:
    from corm.model import Model


class Hook:
    match_entities: t.List['Model']

    def go(self, data, entity: 'Model'):
        raise NotImplementedError