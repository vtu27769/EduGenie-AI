import logging
import json
from datetime import datetime, timedelta
from src.database.db_manager import get_gamification, update_gamification

logger = logging.getLogger(__name__)

# List of all available badges
ALL_BADGES = {
    "🏆 First Step": "Created an account on EduGenie AI.",
    "📚 Scholar": "Uploaded your first study document.",
    "💬 Talkative": "Asked 10 questions in Study Assistant.",
    "📝 Study Genie": "Compiled your first set of comprehensive study notes.",
    "🎯 Quiz Master": "Completed 5 mock quizzes.",
    "🎓 Ace Student": "Scored 100% on any quiz or exam mode assessment.",
    "🔥 7-Day Streak": "Maintained a study streak for 7 consecutive days.",
    "🃏 Memorizer": "Marked 10 flashcards as learned.",
    "📅 Organized": "Generated a personalized study schedule planner.",
    "⏱️ Speed Runner": "Completed a timed Exam Mode challenge."
}

def add_xp(user_id: int, amount: int) -> dict:
    """
    Adds XP to the user's total, automatically handles Level Up calculation.
    Returns status: {"xp_added": amount, "level_up": true/false, "new_level": level, "new_xp": xp}
    """
    stats = get_gamification(user_id)
    old_level = stats["level"]
    new_xp = stats["xp"] + amount
    
    # Calculate new level: 1000 XP per level
    new_level = int(new_xp // 1000) + 1
    
    level_up = (new_level > old_level)
    
    update_gamification(
        user_id, 
        new_xp, 
        new_level, 
        stats["current_streak"], 
        stats["last_active_date"], 
        stats["badges"]
    )
    
    return {
        "xp_added": amount,
        "level_up": level_up,
        "new_level": new_level,
        "new_xp": new_xp
    }

def update_streak(user_id: int) -> dict:
    """
    Updates the user's daily study streak based on activity date.
    Resets if they missed a day, increments if active on consecutive days.
    """
    stats = get_gamification(user_id)
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    current_streak = stats["current_streak"]
    last_active = stats["last_active_date"]
    
    if last_active == today_str:
        # Already logged activity today, do not change streak
        return {"streak_updated": False, "current_streak": current_streak}
        
    if last_active == yesterday_str:
        # Consecutive day active! Increment
        current_streak += 1
    else:
        # Streak broken (either first login or missed a day)
        current_streak = 1
        
    # Check 7-day streak badge
    badge_unlocked = None
    if current_streak >= 7:
        badge_unlocked = award_badge(user_id, "🔥 7-Day Streak")
        
    update_gamification(
        user_id, 
        stats["xp"], 
        stats["level"], 
        current_streak, 
        today_str, 
        stats["badges"]
    )
    
    return {
        "streak_updated": True, 
        "current_streak": current_streak,
        "badge_unlocked": badge_unlocked
    }

def award_badge(user_id: int, badge_name: str) -> bool:
    """
    Awards a badge to the user. Returns True if successfully awarded (was not unlocked yet), False otherwise.
    """
    if badge_name not in ALL_BADGES:
        logger.warning(f"Attempted to award non-existent badge: {badge_name}")
        return False
        
    stats = get_gamification(user_id)
    try:
        badges = json.loads(stats["badges"])
    except Exception:
        badges = []
        
    if badge_name in badges:
        return False # Already unlocked
        
    badges.append(badge_name)
    badges_str = json.dumps(badges)
    
    # Update DB
    update_gamification(
        user_id, 
        stats["xp"], 
        stats["level"], 
        stats["current_streak"], 
        stats["last_active_date"], 
        badges_str
    )
    
    # Award 100 XP for unlocking a badge!
    add_xp(user_id, 100)
    
    logger.info(f"User {user_id} unlocked badge: {badge_name}")
    return True
