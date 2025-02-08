from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, distinct, or_
from . import models

def calculate_popularity_score(db: Session, game_id: int) -> float:
    """
    Calculate game popularity score based on weighted factors:
    - w1 (30%): Number of people who played yesterday / max daily players
    - w2 (20%): Current active players / max concurrent players
    - w3 (25%): Total upvotes / max upvotes
    - w4 (15%): Max session length yesterday / max session length overall
    - w5 (10%): Total sessions yesterday / max daily sessions
    """
    now = datetime.utcnow()
    yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
    yesterday_end = yesterday_start + timedelta(days=1)

    # Get yesterday's players (w1)
    yesterday_players = db.query(func.count(distinct(models.GameSession.contestant_id))).filter(
        models.GameSession.game_id == game_id,
        models.GameSession.start_time >= yesterday_start,
        models.GameSession.start_time < yesterday_end
    ).scalar()

    # Get max daily players across all games
    max_daily_players = db.query(
        func.count(distinct(models.GameSession.contestant_id))
    ).group_by(
        models.GameSession.game_id,
        func.date(models.GameSession.start_time)
    ).order_by(desc(func.count(distinct(models.GameSession.contestant_id)))).first()

    max_daily_players = max_daily_players[0] if max_daily_players else 1  # Avoid division by zero

    # Get current active players (w2)
    current_players = db.query(func.count(distinct(models.GameSession.contestant_id))).filter(
        models.GameSession.game_id == game_id,
        models.GameSession.start_time <= now,
        or_(models.GameSession.end_time == None, models.GameSession.end_time >= now)
    ).scalar()

    # Get max concurrent players
    max_concurrent_players = db.query(
        func.count(distinct(models.GameSession.contestant_id))
    ).filter(
        or_(models.GameSession.end_time == None, models.GameSession.end_time >= models.GameSession.start_time)
    ).group_by(models.GameSession.game_id).order_by(desc(func.count(distinct(models.GameSession.contestant_id)))).first()

    max_concurrent_players = max_concurrent_players[0] if max_concurrent_players else 1

    # Get upvotes (w3)
    upvotes = db.query(func.count(models.GameUpvote.id)).filter(
        models.GameUpvote.game_id == game_id
    ).scalar()

    max_upvotes = db.query(
        func.count(models.GameUpvote.id)
    ).group_by(models.GameUpvote.game_id).order_by(desc(func.count(models.GameUpvote.id))).first()

    max_upvotes = max_upvotes[0] if max_upvotes else 1

    # Get maximum session length yesterday (w4)
    max_session_length_yesterday = db.query(func.max(models.GameSession.session_length)).filter(
        models.GameSession.game_id == game_id,
        models.GameSession.start_time >= yesterday_start,
        models.GameSession.start_time < yesterday_end,
        models.GameSession.session_length != None
    ).scalar() or 0

    max_session_length_overall = db.query(
        func.max(models.GameSession.session_length)
    ).filter(models.GameSession.session_length != None).scalar() or 1

    # Get total sessions yesterday (w5)
    total_sessions_yesterday = db.query(func.count(models.GameSession.id)).filter(
        models.GameSession.game_id == game_id,
        models.GameSession.start_time >= yesterday_start,
        models.GameSession.start_time < yesterday_end
    ).scalar()

    max_daily_sessions = db.query(
        func.count(models.GameSession.id)
    ).group_by(
        models.GameSession.game_id,
        func.date(models.GameSession.start_time)
    ).order_by(desc(func.count(models.GameSession.id))).first()

    max_daily_sessions = max_daily_sessions[0] if max_daily_sessions else 1

    # Calculate weighted score components
    w1_score = 0.3 * (yesterday_players / max_daily_players)
    w2_score = 0.2 * (current_players / max_concurrent_players)
    w3_score = 0.25 * (upvotes / max_upvotes)
    w4_score = 0.15 * (max_session_length_yesterday / max_session_length_overall)
    w5_score = 0.1 * (total_sessions_yesterday / max_daily_sessions)

    # Calculate final score
    popularity_score = w1_score + w2_score + w3_score + w4_score + w5_score

    return {
        "popularity_score": round(popularity_score * 100, 2),  # Convert to percentage
        "components": {
            "daily_players_score": round(w1_score * 100, 2),
            "current_players_score": round(w2_score * 100, 2),
            "upvotes_score": round(w3_score * 100, 2),
            "session_length_score": round(w4_score * 100, 2),
            "daily_sessions_score": round(w5_score * 100, 2)
        },
        "metrics": {
            "yesterday_players": yesterday_players,
            "current_players": current_players,
            "total_upvotes": upvotes,
            "max_session_length_yesterday": max_session_length_yesterday,
            "total_sessions_yesterday": total_sessions_yesterday
        }
    }
