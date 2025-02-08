from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, distinct
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from jwt.exceptions import InvalidTokenError

from . import models, schemas
from .database import engine, get_db

# App Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="GameLeadertrack API")
ROOT_DIR = Path(__file__).resolve().parent.parent

# Security Configuration
SECRET_KEY = "your-secret-key-keep-it-safe"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Static Files
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))

# Helper Functions
def create_access_token(data: dict):
    expires = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expires}, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not (username := payload.get("sub")):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        if not (user := db.query(models.User).filter(models.User.username == username).first()):
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Route Handlers
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/contestants/", response_model=schemas.ContestantResponse)
def create_contestant(contestant: schemas.ContestantCreate, db: Session = Depends(get_db)):
    try:
        db_contestant = models.Contestant(**contestant.dict())
        db.add(db_contestant)
        db.commit()
        db.refresh(db_contestant)
        logger.info(f"Created contestant: {contestant.name}")
        return db_contestant
    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: contestants.email" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/contestants/", response_model=List[schemas.ContestantResponse])
def get_contestants(db: Session = Depends(get_db)):
    return db.query(models.Contestant).all()

@app.post("/games/", response_model=schemas.GameResponse)
def create_game(game: schemas.GameCreate, db: Session = Depends(get_db)):
    db_game = models.Game(**game.dict())
    db.add(db_game)
    db.commit()
    db.refresh(db_game)
    return db_game

@app.get("/games/", response_model=List[schemas.GameResponse])
def get_games(db: Session = Depends(get_db)):
    return db.query(models.Game).all()

@app.delete("/games/{game_id}")
def delete_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(models.Game).filter(models.Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    db.delete(game)
    db.commit()
    return {"message": "Game deleted successfully"}

@app.get("/games/popularity/")
async def get_games_popularity(db: Session = Depends(get_db)):
    # Get current time for calculations
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Get statistics for each game
    games_stats = []
    games = db.query(models.Game).all()

    for game in games:
        # Get total scores and players
        total_scores = db.query(models.Score).filter(
            models.Score.game_id == game.id
        ).count()

        unique_players = db.query(func.count(distinct(models.Score.contestant_id))).filter(
            models.Score.game_id == game.id
        ).scalar()

        # Get recent activity
        recent_scores = db.query(models.Score).filter(
            models.Score.game_id == game.id,
            models.Score.timestamp >= week_ago
        ).count()

        # Get last month's activity for trend comparison
        last_month_scores = db.query(models.Score).filter(
            models.Score.game_id == game.id,
            models.Score.timestamp >= month_ago,
            models.Score.timestamp < week_ago
        ).count()

        # Calculate trends
        score_trend = 0
        if last_month_scores > 0:
            score_trend = (recent_scores - last_month_scores) / last_month_scores

        # Get last played timestamp
        last_played = db.query(func.max(models.Score.timestamp)).filter(
            models.Score.game_id == game.id
        ).scalar()

        # Calculate popularity score (you can adjust the weights)
        recency_weight = 1.0 if last_played and (now - last_played).days < 7 else 0.5
        activity_score = (recent_scores * 0.7 + total_scores * 0.3) * recency_weight
        player_score = unique_players * 2
        popularity_score = (activity_score + player_score) / 3

        games_stats.append({
            "id": game.id,
            "name": game.name,
            "popularity_score": popularity_score,
            "total_scores": total_scores,
            "unique_players": unique_players,
            "recent_scores": recent_scores,
            "last_played": last_played.isoformat() if last_played else None,
            "score_trend": score_trend,
            "is_active": game.is_active
        })

    # Sort by popularity score
    games_stats.sort(key=lambda x: x["popularity_score"], reverse=True)
    return games_stats

@app.put("/games/{game_id}/start")
def start_game(game_id: int, db: Session = Depends(get_db)):
    if not (game := db.query(models.Game).filter(models.Game.id == game_id).first()):
        raise HTTPException(status_code=404, detail="Game not found")
    setattr(game, 'is_active', True)
    db.commit()
    return {"message": "Game started"}

@app.put("/games/{game_id}/end")
def end_game(game_id: int, db: Session = Depends(get_db)):
    if not (game := db.query(models.Game).filter(models.Game.id == game_id).first()):
        raise HTTPException(status_code=404, detail="Game not found")
    setattr(game, 'is_active', False)
    db.commit()
    return {"message": "Game ended"}

@app.post("/scores/", response_model=schemas.ScoreResponse)
def create_score(score_data: schemas.ScoreCreate, db: Session = Depends(get_db)):
    if not (game := db.query(models.Game).filter(models.Game.id == score_data.game_id).first()):
        raise HTTPException(status_code=404, detail="Game not found")
    if not getattr(game, 'is_active'):
        raise HTTPException(status_code=400, detail="Game is not active")

    score_entry = models.Score(**score_data.dict())
    db.add(score_entry)
    db.commit()
    db.refresh(score_entry)
    return score_entry

@app.get("/leaderboard/")
def get_leaderboard(game_id: Optional[int] = None, date: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(
        models.Contestant.name.label("contestant_name"),
        models.Game.name.label("game_name"),
        models.Score.score,
        models.Score.timestamp
    ).join(models.Score.contestant).join(models.Score.game)

    if game_id:
        query = query.filter(models.Score.game_id == game_id)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            query = query.filter(
                models.Score.timestamp >= target_date,
                models.Score.timestamp < target_date + timedelta(days=1)
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    results = query.order_by(desc(models.Score.score)).all()
    return [{"contestant_name": r.contestant_name, "game_name": r.game_name,
             "score": r.score, "timestamp": r.timestamp.isoformat()} for r in results]

@app.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = models.User(username=user.username, email=user.email)
    db_user.set_password(user.password)
    try:
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError as e:
        db.rollback()
        if "users.email" in str(e):
            raise HTTPException(status_code=400, detail="Email already registered")
        if "users.username" in str(e):
            raise HTTPException(status_code=400, detail="Username already taken")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if not (user := db.query(models.User).filter(models.User.username == form_data.username).first()):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.check_password(form_data.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_access_token({"sub": user.username}), "token_type": "bearer"}

@app.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user

@app.get("/game-dashboard/")
async def game_dashboard(request: Request):
    return templates.TemplateResponse("game_dashboard.html", {"request": request})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
