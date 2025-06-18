# Internal
import typing as T
from typing import List, Optional

# External
from pydantic.dataclasses import dataclass

@dataclass
class UserOpinion:
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    opinions: List[str] = None
    my_mood_with_him: float = 0.0
    
    def __post_init__(self):
        if self.opinions is None:
            self.opinions = []