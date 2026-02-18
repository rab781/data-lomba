"""
FastAPI competitions router.
Handles listing, searching, filtering, and detail endpoints.
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database.schema import get_db, Competition, CompetitionEvent, Organizer
from api.schemas import (
    CompetitionBase, CompetitionDetail,
    PaginatedCompetitions, OrganizerBase, CompetitionEventBase
)

router = APIRouter(prefix="/competitions", tags=["competitions"])


def _apply_filters(query, level, sector, cluster, comp_type, rating_min,
                   rating_max, country_code, year_start, year_end):
    """Apply common filter params to a SQLAlchemy query."""
    if level:
        query = query.filter(Competition.level == level)
    if sector:
        query = query.filter(Competition.sector == sector)
    if cluster:
        query = query.filter(Competition.cluster == cluster)
    if comp_type:
        query = query.filter(Competition.type == comp_type)
    if rating_min is not None:
        query = query.filter(Competition.rating >= rating_min)
    if rating_max is not None:
        query = query.filter(Competition.rating <= rating_max)
    # Only join CompetitionEvent once if any event-based filter is needed
    if country_code or year_start or year_end:
        query = query.join(CompetitionEvent, Competition.competition_id == CompetitionEvent.id)
        if country_code:
            query = query.filter(CompetitionEvent.country_code == country_code)
        if year_start:
            query = query.filter(func.strftime('%Y', CompetitionEvent.competition_start) >= str(year_start))
        if year_end:
            query = query.filter(func.strftime('%Y', CompetitionEvent.competition_start) <= str(year_end))
    return query


@router.get("", response_model=PaginatedCompetitions)
def list_competitions(
    db:           Session = Depends(get_db),
    page:         int     = Query(1,  ge=1),
    per_page:     int     = Query(20, ge=1, le=100),
    sort_by:      str     = Query("score", pattern="^(score|rating|id)$"),
    order:        str     = Query("desc", pattern="^(asc|desc)$"),
    # Filters
    level:        str     = Query(None),
    sector:       str     = Query(None),
    cluster:      str     = Query(None),
    comp_type:    str     = Query(None, alias="type"),
    rating_min:   int     = Query(None, ge=0, le=5),
    rating_max:   int     = Query(None, ge=0, le=5),
    country_code: str     = Query(None),
    year_start:   int     = Query(None),
    year_end:     int     = Query(None),
):
    q = db.query(Competition)
    q = _apply_filters(q, level, sector, cluster, comp_type,
                       rating_min, rating_max, country_code, year_start, year_end)

    total = q.count()
    col   = getattr(Competition, sort_by)
    q     = q.order_by(col.desc() if order == "desc" else col.asc())
    items = q.offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedCompetitions(
        total    = total,
        page     = page,
        per_page = per_page,
        pages    = math.ceil(total / per_page),
        items    = items,
    )


@router.get("/search", response_model=PaginatedCompetitions)
def search_competitions(
    q_str:    str     = Query(..., alias="q", min_length=2),
    db:       Session = Depends(get_db),
    page:     int     = Query(1, ge=1),
    per_page: int     = Query(20, ge=1, le=100),
    level:    str     = Query(None),
    sector:   str     = Query(None),
    rating_min: int   = Query(None, ge=0, le=5),
):
    keyword = f"%{q_str}%"
    q = db.query(Competition).join(
        CompetitionEvent, Competition.competition_id == CompetitionEvent.id, isouter=True
    ).join(
        Organizer, Competition.organizer_id == Organizer.id, isouter=True
    ).filter(
        or_(
            Competition.branch.ilike(keyword),
            CompetitionEvent.name.ilike(keyword),
            Organizer.name.ilike(keyword),
            CompetitionEvent.short_name.ilike(keyword),
        )
    )
    if level:
        q = q.filter(Competition.level == level)
    if sector:
        q = q.filter(Competition.sector == sector)
    if rating_min is not None:
        q = q.filter(Competition.rating >= rating_min)

    total = q.count()
    items = q.order_by(Competition.score.desc())\
             .offset((page - 1) * per_page).limit(per_page).all()

    return PaginatedCompetitions(
        total    = total,
        page     = page,
        per_page = per_page,
        pages    = math.ceil(total / per_page),
        items    = items,
    )


@router.get("/{comp_id}", response_model=CompetitionDetail)
def get_competition(comp_id: int, db: Session = Depends(get_db)):
    item = db.query(Competition).filter(Competition.id == comp_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Competition not found")

    event = db.get(CompetitionEvent, item.competition_id)
    org   = db.get(Organizer, item.organizer_id)

    # Build dict manually to avoid ORM relationship attribute conflicts
    result_data = {
        "id":             item.id,
        "branch_id":      item.branch_id,
        "branch":         item.branch,
        "competition_id": item.competition_id,
        "organizer_id":   item.organizer_id,
        "category":       item.category,
        "level":          item.level,
        "type":           item.type,
        "sector":         item.sector,
        "cluster":        item.cluster,
        "score":          item.score,
        "rating":         item.rating,
        "batch_raw":      item.batch_raw,
        "batch_num":      item.batch_num,
        "batch_year":     item.batch_year,
        "created_at":     item.created_at,
        "updated_at":     item.updated_at,
        "event":          CompetitionEventBase.model_validate(event, from_attributes=True).model_dump() if event else None,
        "organizer":      OrganizerBase.model_validate(org, from_attributes=True).model_dump() if org else None,
    }
    return CompetitionDetail.model_validate(result_data)


@router.get("/filters/options")
def get_filter_options(db: Session = Depends(get_db)):
    """Return all unique filter values for frontend dropdowns."""
    levels   = [r[0] for r in db.query(Competition.level).distinct() if r[0]]
    sectors  = [r[0] for r in db.query(Competition.sector).distinct() if r[0]]
    clusters = [r[0] for r in db.query(Competition.cluster).distinct() if r[0]]
    types    = [r[0] for r in db.query(Competition.type).distinct() if r[0]]
    years    = sorted([
        r[0] for r in db.query(func.strftime('%Y', CompetitionEvent.competition_start)).distinct()
        if r[0]
    ])
    countries = [
        {"code": r[0], "name": r[1]}
        for r in db.query(CompetitionEvent.country_code, CompetitionEvent.country).distinct()
        if r[0]
    ]

    return {
        "levels":    sorted(levels),
        "sectors":   sorted(sectors),
        "clusters":  sorted(clusters),
        "types":     sorted(types),
        "years":     years,
        "countries": sorted(countries, key=lambda x: x["name"]),
    }
