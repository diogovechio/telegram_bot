# Internal
import typing as T
from datetime import datetime
from uuid import UUID

# External
from pydantic.dataclasses import dataclass
from pydantic import Field

# Project


@dataclass
class Agenda:
    """
    Dataclass representing a commemoration event.
    
    This class models the structure found in old_data/commemorations.json.
    It represents events that should be celebrated at specific times with
    configurable frequency (annual, monthly, or once).
    """
    id: str
    frequency: str  # "annual", "monthly", "once"
    created_by: int
    created_at: datetime
    celebrate_at: datetime
    for_chat: int
    message: str = ""
    anniversary: str = ""
    last_celebration: T.Optional[datetime] = None