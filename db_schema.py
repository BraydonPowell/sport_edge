"""
Database schema definition for Sports Edge MVP.
Uses SQLAlchemy ORM for database abstraction.
"""

from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()


class Game(Base):
    __tablename__ = "games"

    game_id = Column(String, primary_key=True)
    date = Column(DateTime, nullable=False, index=True)
    league = Column(String, nullable=False)
    home_team = Column(String, nullable=False, index=True)
    away_team = Column(String, nullable=False, index=True)
    home_score = Column(Integer)
    away_score = Column(Integer)
    winner = Column(String)  # "home", "away", or "draw"

    odds = relationship("Odds", back_populates="game")
    predictions = relationship("Prediction", back_populates="game")


class Odds(Base):
    __tablename__ = "odds"

    odds_id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.game_id"), nullable=False, index=True)
    book = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    home_ml = Column(Float)  # American odds
    away_ml = Column(Float)  # American odds
    source = Column(String)  # e.g., "closing", "opening", "api_snapshot"

    game = relationship("Game", back_populates="odds")


class TeamRating(Base):
    __tablename__ = "team_ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    elo = Column(Float)
    # Optional: add other rating systems or rolling stats


class Prediction(Base):
    __tablename__ = "predictions"

    pred_id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.game_id"), nullable=False, index=True)
    model_version = Column(String, nullable=False)
    decision_time = Column(DateTime, nullable=False)
    p_home = Column(Float, nullable=False)
    p_away = Column(Float, nullable=False)

    game = relationship("Game", back_populates="predictions")


class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    run_id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    config_json = Column(Text, nullable=False)
    metrics_json = Column(Text, nullable=False)


def get_engine(database_url=None):
    """Create and return database engine."""
    if database_url is None:
        database_url = os.getenv("DATABASE_URL", "sqlite:///data/sports_edge.db")
    return create_engine(database_url)


def init_db(database_url=None):
    """Initialize database schema."""
    engine = get_engine(database_url)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine=None):
    """Get database session."""
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing database schema...")
    engine = init_db()
    print(f"Database initialized at: {engine.url}")
