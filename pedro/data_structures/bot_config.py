# Internal
import typing as T

# External
from pydantic.dataclasses import dataclass

# Project


@dataclass
class Chats:
    name: str
    id: int


@dataclass
class BotSecret:
    bot_token: str
    openai_key: str


@dataclass
class BotConfig:
    allowed_ids: list[Chats]
    secrets: BotSecret
