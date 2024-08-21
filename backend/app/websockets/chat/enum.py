from enum import Enum as PyEnum
from ..base import WSResponseTypeEnum


class QARequestTypeEnum(str, PyEnum):
    MESSAGE = "message"
    CONFIG = "config"

class QAResponseTypeEnum(str, PyEnum):
    ERROR = WSResponseTypeEnum.ERROR.value
    MESSAGE_STREAM = "message_stream"
    MESSAGE_END = "message_end"