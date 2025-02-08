from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from werkzeug.security import generate_password_hash, check_password_hash
from .database import Base

class User( Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(120), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(256))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Contestant(Base):
    __tablename__ = "contestants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scores = relationship("Score", back_populates="contestant")

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scores = relationship("Score", back_populates="game")

class Score(Base):
    __tablename__ = "scores"

    id = Column(Integer, primary_key=True, index=True)
    contestant_id = Column(Integer, ForeignKey("contestants.id"), nullable=False)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    score = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    contestant = relationship("Contestant", back_populates="scores")
    game = relationship("Game", back_populates="scores")


class GameSession(Base):
    __tablename__ = "game_sessions"
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    contestant_id = Column(Integer, ForeignKey("contestants.id"))
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    session_length = Column(Integer, nullable=True)  # in minutes

class GameUpvote(Base):
    __tablename__ = "game_upvotes"
    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey("games.id"))
    contestant_id = Column(Integer, ForeignKey("contestants.id"))
    timestamp = Column(DateTime, default=func.now())
