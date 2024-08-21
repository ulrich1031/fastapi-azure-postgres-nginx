from enum import Enum as PyEnum


class ChunkTypeEnum(PyEnum):
    INTERNAL = "INTERNAL"
    WEB = "WEB"
    FILE = "FILE"
    URL = "URL"