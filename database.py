import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, String, Float, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.mysql import CHAR
from uuid import uuid4
from datetime import datetime
import enum

load_dotenv()

Base = declarative_base()


class OriginEnum(str, enum.Enum):
    home = "home"
    cafe = "cafe"


class RankedItemDB(Base):
    __tablename__ = "ranked_items"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    ranking_id = Column(CHAR(36), ForeignKey("rankings.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    origin = Column(SQLEnum(OriginEnum), nullable=False)
    rating = Column(Float, nullable=False)
    cost_per_gram = Column(Float, nullable=False)

    # Relationship
    ranking = relationship("RankingDB", back_populates="items")


class RankingDB(Base):
    __tablename__ = "rankings"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(CHAR(36), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship
    items = relationship("RankedItemDB", back_populates="ranking", cascade="all, delete-orphan")


# Database connection setup
def get_database_url():
    """
    Get database URL from environment variables.
    Supports both local development and Cloud Run with Cloud SQL.
    """

    if os.getenv("CLOUD_SQL_CONNECTION_NAME"):
        connection_name = os.getenv("CLOUD_SQL_CONNECTION_NAME")
        db_user = os.getenv("DB_USER", "appuser")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME", "matchamania")

        return f"mysql+pymysql://{db_user}:{db_password}@/{db_name}?unix_socket=/cloudsql/{connection_name}"
    else:
        # Local development or direct TCP connection
        db_host = os.getenv("DB_HOST", "127.0.0.1")
        db_port = os.getenv("DB_PORT", "3307")
        db_user = os.getenv("DB_USER", "appuser")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME", "matchamania")

        return f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


# Create engine
DATABASE_URL = get_database_url()
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=False  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency to get database session.
    Use with FastAPI Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Call this on application startup.
    """
    Base.metadata.create_all(bind=engine)