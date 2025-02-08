from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

class UserBase(BaseModel):
    username: str
    email: EmailStr

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    username: str
    password: str

class ContestantBase(BaseModel):
    name: str
    email: EmailStr

class ContestantCreate(ContestantBase):
    pass

class ContestantResponse(ContestantBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

class GameBase(BaseModel):
    name: str

class GameCreate(GameBase):
    pass

class GameResponse(GameBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

class ScoreBase(BaseModel):
    contestant_id: int
    game_id: int
    score: float

class ScoreCreate(ScoreBase):
    pass

class ScoreResponse(ScoreBase):
    id: int
    timestamp: datetime

    class Config:
        orm_mode = True

class LeaderboardEntry(BaseModel):
    contestant_name: str
    game_name: str
    score: float
    timestamp: datetime

    class Config:
        orm_mode = True