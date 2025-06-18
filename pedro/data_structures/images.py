from pydantic.dataclasses import dataclass

@dataclass
class MessageImage:
    bytes: bytes
    url: str