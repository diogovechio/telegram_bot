from pydantic.dataclasses import dataclass

@dataclass
class MessageImage:
    bytes: bytes
    url: str
    from_doc: bool = False

@dataclass
class MessageDocument:
    bytes: bytes
    url: str
    file_name: str
    mime_type: str
