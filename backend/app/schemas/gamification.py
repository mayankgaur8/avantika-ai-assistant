from pydantic import BaseModel
from typing import List, Optional

class UserProgress(BaseModel):
    user_id: str
    total_xp: int
    streak_days: int
    level: int
    xp_to_next_level: int
    active_badges: List[str]

class ProgressUpdate(BaseModel):
    xp_gained: int
    activity_type: str
