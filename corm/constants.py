import enum


class AccessMode(int, enum.Enum):
    GET = 1
    SET = 1 << 1
    LOAD = 1 << 2
    DUMP = 1 << 3

    GET_LOAD = GET | LOAD
    GET_DUMP = GET | DUMP
    SET_LOAD = SET | LOAD
    GET_LOAD_DUMP = GET | LOAD | DUMP

    ALL = GET | SET | LOAD | DUMP


class RelationType(int, enum.Enum):
    PARENT = 1
    CHILD = 2
    RELATED = 3
