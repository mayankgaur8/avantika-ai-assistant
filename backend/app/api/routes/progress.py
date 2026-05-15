from fastapi import APIRouter, Depends, HTTPException
from app.schemas.gamification import UserProgress, ProgressUpdate

router = APIRouter(prefix="/user", tags=["gamification"])

# Mock database for progress
MOCK_PROGRESS = {
    "user_1": {
        "user_id": "user_1",
        "total_xp": 1450,
        "streak_days": 12,
        "level": 4,
        "xp_to_next_level": 550,
        "active_badges": ["Early Bird", "Grammar Master"]
    }
}

@router.get("/progress", response_model=UserProgress)
async def get_user_progress(user_id: str = "user_1"):
    """
    Handle gamification data: Streaks, total XP, and active Badges.
    """
    progress = MOCK_PROGRESS.get(user_id)
    if not progress:
        return UserProgress(
            user_id=user_id,
            total_xp=0,
            streak_days=0,
            level=1,
            xp_to_next_level=1000,
            active_badges=[]
        )
    return progress

@router.post("/progress/update", response_model=UserProgress)
async def update_user_progress(update: ProgressUpdate, user_id: str = "user_1"):
    progress = MOCK_PROGRESS.get(user_id, {
        "user_id": user_id,
        "total_xp": 0,
        "streak_days": 1,
        "level": 1,
        "xp_to_next_level": 1000,
        "active_badges": []
    })
    
    progress["total_xp"] += update.xp_gained
    # Mock level up logic
    if progress["total_xp"] >= 2000:
        progress["level"] = 5
        progress["xp_to_next_level"] = 3000 - progress["total_xp"]
    else:
        progress["xp_to_next_level"] -= update.xp_gained
        
    MOCK_PROGRESS[user_id] = progress
    return progress
