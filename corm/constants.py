import enum


class RelationType(enum.Enum):
    CHILD_OF = 'CHILD_OF'
    PARENT_OF = 'PARENT_OF'
    RELATED = 'RELATED'


class AccessMode:
    GET = 1
    SET = 1 << 1
    LOAD = 1 << 2
    DUMP = 1 << 3

    GET_LOAD = GET | LOAD
    GET_DUMP = GET | DUMP
    SET_LOAD = SET | LOAD
    GET_LOAD_DUMP = GET | LOAD | DUMP

    ALL = GET | SET | LOAD | DUMP