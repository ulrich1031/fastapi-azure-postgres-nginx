from enum import Enum as PyEnum


class MessageRoleEnum(PyEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    
class MessageTypeEnum(PyEnum):
    REPORT = "report"
    QUESTION = "question"