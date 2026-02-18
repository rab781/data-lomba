"""
SQLAlchemy ORM models for SIMT Kompetisi database.
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, ForeignKey, Text, Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from pathlib import Path

Base = declarative_base()

DB_PATH = Path(__file__).parent / "kompetisi.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─────────────────────────────────────────────
# Table: Organizers  (deduplicated)
# ─────────────────────────────────────────────
class Organizer(Base):
    __tablename__ = "organizers"

    id          = Column(String, primary_key=True)   # UUID from source
    name        = Column(String, nullable=False)
    short_name  = Column(String)
    useful_link = Column(Text)

    competitions = relationship("Competition", back_populates="organizer_rel")


# ─────────────────────────────────────────────
# Table: Competition Events  (deduplicated by competition_id)
# ─────────────────────────────────────────────
class CompetitionEvent(Base):
    __tablename__ = "competition_events"

    id                    = Column(String, primary_key=True)  # UUID competition_id
    name                  = Column(String, nullable=False)
    short_name            = Column(String)
    competition_start     = Column(DateTime)
    competition_end       = Column(DateTime)
    country               = Column(String)
    country_code          = Column(String(5))
    useful_link           = Column(Text)

    branches = relationship("Competition", back_populates="event_rel")


# ─────────────────────────────────────────────
# Table: Competitions  (one row per branch/entry)
# ─────────────────────────────────────────────
class Competition(Base):
    __tablename__ = "competitions"

    id              = Column(Integer, primary_key=True)   # original id
    branch_id       = Column(Integer, index=True)
    branch          = Column(String, nullable=False)

    # FK relations
    competition_id  = Column(String, ForeignKey("competition_events.id"), index=True)
    organizer_id    = Column(String, ForeignKey("organizers.id"), index=True)

    # Categorization
    category        = Column(String, index=True)
    level           = Column(String, index=True)
    type            = Column(String, index=True)           # Individu / Kelompok
    sector          = Column(String, index=True)
    cluster         = Column(String, index=True)

    # Scoring
    score           = Column(Float, index=True)
    rating          = Column(Integer, index=True)

    # Batch (parsed)
    batch_raw       = Column(String)                       # original string
    batch_num       = Column(Integer)
    batch_year      = Column(Integer, index=True)

    # Timestamps
    created_at      = Column(DateTime)
    updated_at      = Column(DateTime)

    # Relationships
    event_rel       = relationship("CompetitionEvent", back_populates="branches")
    organizer_rel   = relationship("Organizer", back_populates="competitions")

    __table_args__ = (
        Index("ix_comp_level_sector",  "level", "sector"),
        Index("ix_comp_level_cluster", "level", "cluster"),
        Index("ix_comp_rating_score",  "rating", "score"),
    )


def init_db():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI: yield DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
