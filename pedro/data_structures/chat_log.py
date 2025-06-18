# Internal
from datetime import datetime

# External
from pydantic.dataclasses import dataclass


@dataclass
class ChatLog:
    user_id: str
    username: str | None
    first_name: str
    last_name: str
    datetime: str
    message: str