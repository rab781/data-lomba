"""
Pydantic schemas for FastAPI request/response validation.
"""
from pydantic import BaseModel
from typing import Optional, Sequence
from datetime import datetime


# ── Organizer ──────────────────────────────────────
class OrganizerBase(BaseModel):
    id:          str
    name:        str
    short_name:  Optional[str] = None
    useful_link: Optional[str] = None

class OrganizerSummary(OrganizerBase):
    competition_count: int
    avg_score:         Optional[float] = None
    avg_rating:        Optional[float] = None

    model_config = {"from_attributes": True}


# ── Competition Event ───────────────────────────────
class CompetitionEventBase(BaseModel):
    id:                str
    name:              str
    short_name:        Optional[str]    = None
    competition_start: Optional[datetime] = None
    competition_end:   Optional[datetime] = None
    country:           Optional[str]    = None
    country_code:      Optional[str]    = None
    useful_link:       Optional[str]    = None

    model_config = {"from_attributes": True}


# ── Competition Branch ──────────────────────────────
class CompetitionBase(BaseModel):
    id:             int
    branch_id:      Optional[int]   = None
    branch:         str
    competition_id: str
    organizer_id:   str
    category:       Optional[str]   = None
    level:          Optional[str]   = None
    type:           Optional[str]   = None
    sector:         Optional[str]   = None
    cluster:        Optional[str]   = None
    score:          Optional[float] = None
    rating:         Optional[int]   = None
    batch_raw:      Optional[str]   = None
    batch_num:      Optional[int]   = None
    batch_year:     Optional[int]   = None
    created_at:     Optional[datetime] = None
    updated_at:     Optional[datetime] = None

    model_config = {"from_attributes": True}


class CompetitionDetail(CompetitionBase):
    """Full detail: includes nested event and organizer."""
    event:     Optional[CompetitionEventBase] = None
    organizer: Optional[OrganizerBase]        = None

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Pagination wrapper ──────────────────────────────
class PaginatedCompetitions(BaseModel):
    total:    int
    page:     int
    per_page: int
    pages:    int
    items:    Sequence[CompetitionBase]


# ── Analytics schemas ───────────────────────────────
class CountAvgItem(BaseModel):
    label:      str
    count:      int
    avg_score:  Optional[float] = None
    avg_rating: Optional[float] = None

class OverviewStats(BaseModel):
    total_competitions:      int
    total_events:            int
    total_organizers:        int
    total_countries:         int
    avg_score:               float
    score_min:               float
    score_max:               float
    level_distribution:      list[CountAvgItem]
    cluster_distribution:    list[CountAvgItem]
    type_distribution:       list[CountAvgItem]

class ScoreBucketItem(BaseModel):
    rating:  int
    count:   int
    min_score: float
    max_score: float
    avg_score: float
