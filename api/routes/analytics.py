"""
FastAPI analytics router.
Provides aggregated statistics and insights from the database.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database.schema import get_db, Competition, CompetitionEvent, Organizer
from api.schemas import OverviewStats, CountAvgItem, OrganizerSummary, ScoreBucketItem

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(db: Session = Depends(get_db)):
    total_comp  = db.query(Competition).count()
    total_evt   = db.query(CompetitionEvent).count()
    total_org   = db.query(Organizer).count()
    total_cntry = db.query(CompetitionEvent.country_code).distinct().count()

    stats = db.query(
        func.avg(Competition.score),
        func.min(Competition.score),
        func.max(Competition.score),
    ).first()
    avg_score_val = stats[0] if stats is not None else None
    min_score_val = stats[1] if stats is not None else None
    max_score_val = stats[2] if stats is not None else None

    def distribution(col):
        rows = db.query(
            col,
            func.count(Competition.id),
            func.avg(Competition.score),
            func.avg(Competition.rating),
        ).group_by(col).order_by(func.count(Competition.id).desc()).all()
        return [
            CountAvgItem(
                label      = str(r[0]) if r[0] else "Unknown",
                count      = r[1],
                avg_score  = round(r[2], 3) if r[2] else None,
                avg_rating = round(r[3], 2) if r[3] else None,
            )
            for r in rows
        ]

    return OverviewStats(
        total_competitions   = total_comp,
        total_events         = total_evt,
        total_organizers     = total_org,
        total_countries      = total_cntry,
        avg_score            = round(avg_score_val or 0, 3),
        score_min            = round(min_score_val or 0, 3),
        score_max            = round(max_score_val or 0, 3),
        level_distribution   = distribution(Competition.level),
        cluster_distribution = distribution(Competition.cluster),
        type_distribution    = distribution(Competition.type),
    )


@router.get("/by-sector")
def by_sector(db: Session = Depends(get_db)):
    rows = db.query(
        Competition.sector,
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
        func.avg(Competition.rating).label("avg_rating"),
    ).group_by(Competition.sector).order_by(func.count(Competition.id).desc()).all()

    return [
        {"sector": r[0] or "Unknown", "count": r[1],
         "avg_score": round(r[2], 3) if r[2] else None,
         "avg_rating": round(r[3], 2) if r[3] else None}
        for r in rows
    ]


@router.get("/by-level")
def by_level(db: Session = Depends(get_db)):
    rows = db.query(
        Competition.level,
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
        func.avg(Competition.rating).label("avg_rating"),
        func.min(Competition.score).label("min_score"),
        func.max(Competition.score).label("max_score"),
    ).group_by(Competition.level).all()

    return [
        {"level": r[0] or "Unknown", "count": r[1],
         "avg_score": round(r[2], 3) if r[2] else None,
         "avg_rating": round(r[3], 2) if r[3] else None,
         "min_score": round(r[4], 3) if r[4] else None,
         "max_score": round(r[5], 3) if r[5] else None}
        for r in rows
    ]


@router.get("/by-country")
def by_country(db: Session = Depends(get_db)):
    rows = db.query(
        CompetitionEvent.country,
        CompetitionEvent.country_code,
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
    ).join(Competition, Competition.competition_id == CompetitionEvent.id)\
     .group_by(CompetitionEvent.country_code)\
     .order_by(func.count(Competition.id).desc()).all()

    return [
        {"country": r[0], "country_code": r[1], "count": r[2],
         "avg_score": round(r[3], 3) if r[3] else None}
        for r in rows
    ]


@router.get("/by-year")
def by_year(db: Session = Depends(get_db)):
    rows = db.query(
        func.strftime('%Y', CompetitionEvent.competition_start).label("year"),
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
    ).join(Competition, Competition.competition_id == CompetitionEvent.id)\
     .filter(CompetitionEvent.competition_start.isnot(None))\
     .group_by("year").order_by("year").all()

    return [
        {"year": r[0], "count": r[1],
         "avg_score": round(r[2], 3) if r[2] else None}
        for r in rows
    ]


@router.get("/top-organizers")
def top_organizers(
    db:    Session = Depends(get_db),
    limit: int     = 20,
    order: str     = "avg_score",  # avg_score | count
):
    rows = db.query(
        Organizer.id,
        Organizer.name,
        Organizer.short_name,
        func.count(Competition.id).label("competition_count"),
        func.avg(Competition.score).label("avg_score"),
        func.avg(Competition.rating).label("avg_rating"),
    ).join(Competition, Competition.organizer_id == Organizer.id)\
     .group_by(Organizer.id)

    sort_col = func.avg(Competition.score) if order == "avg_score" else func.count(Competition.id)
    rows = rows.order_by(sort_col.desc()).limit(limit).all()

    return [
        {"id": r[0], "name": r[1], "short_name": r[2],
         "competition_count": r[3],
         "avg_score": round(r[4], 3) if r[4] else None,
         "avg_rating": round(r[5], 2) if r[5] else None}
        for r in rows
    ]


@router.get("/score-distribution")
def score_distribution(db: Session = Depends(get_db)):
    """Score grouped by rating bucket — supports violin/box plot."""
    rows = db.query(
        Competition.rating,
        func.count(Competition.id).label("count"),
        func.min(Competition.score).label("min_score"),
        func.max(Competition.score).label("max_score"),
        func.avg(Competition.score).label("avg_score"),
    ).filter(Competition.score.isnot(None))\
     .group_by(Competition.rating).order_by(Competition.rating).all()

    return [
        ScoreBucketItem(
            rating    = r[0] if r[0] is not None else -1,
            count     = r[1],
            min_score = round(r[2], 3),
            max_score = round(r[3], 3),
            avg_score = round(r[4], 3),
        )
        for r in rows
    ]


@router.get("/organizer-quality")
def organizer_quality(db: Session = Depends(get_db)):
    """
    All organizers with competition count + avg score.
    Useful for scatter plot to identify 'pabrik lomba' (high volume, low score).
    """
    rows = db.query(
        Organizer.id,
        Organizer.name,
        Organizer.short_name,
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
        func.avg(Competition.rating).label("avg_rating"),
    ).join(Competition, Competition.organizer_id == Organizer.id)\
     .group_by(Organizer.id)\
     .order_by(func.count(Competition.id).desc()).all()

    return [
        {
            "id":            r[0],
            "name":          r[1],
            "short_name":    r[2],
            "count":         r[3],
            "avg_score":     round(r[4], 3) if r[4] else None,
            "avg_rating":    round(r[5], 2) if r[5] else None,
            "is_flagged":    r[3] >= 20 and (r[4] or 100) < 45,   # "pabrik lomba" flag
        }
        for r in rows
    ]


@router.get("/intra-competition-variance")
def intra_competition_variance(db: Session = Depends(get_db), limit: int = 20):
    """
    Events with highest score variance across their branches.
    Shows which competitions have inconsistent branch quality.
    """
    rows = db.query(
        CompetitionEvent.id,
        CompetitionEvent.name,
        func.count(Competition.id).label("branch_count"),
        func.avg(Competition.score).label("avg_score"),
        func.max(Competition.score).label("max_score"),
        func.min(Competition.score).label("min_score"),
        (func.max(Competition.score) - func.min(Competition.score)).label("score_range"),
    ).join(Competition, Competition.competition_id == CompetitionEvent.id)\
     .group_by(CompetitionEvent.id)\
     .having(func.count(Competition.id) > 2)\
     .order_by((func.max(Competition.score) - func.min(Competition.score)).desc())\
     .limit(limit).all()

    return [
        {
            "event_id":     r[0], "event_name": r[1],
            "branch_count": r[2],
            "avg_score":    round(r[3], 3) if r[3] else None,
            "max_score":    round(r[4], 3) if r[4] else None,
            "min_score":    round(r[5], 3) if r[5] else None,
            "score_range":  round(r[6], 3) if r[6] else None,
        }
        for r in rows
    ]


@router.get("/by-batch")
def by_batch(db: Session = Depends(get_db)):
    rows = db.query(
        Competition.batch_year,
        Competition.batch_num,
        func.count(Competition.id).label("count"),
        func.avg(Competition.score).label("avg_score"),
    ).filter(Competition.batch_num.isnot(None))\
     .group_by(Competition.batch_year, Competition.batch_num)\
     .order_by(Competition.batch_year, Competition.batch_num).all()

    return [
        {"batch_year": r[0], "batch_num": r[1], "count": r[2],
         "avg_score": round(r[3], 3) if r[3] else None}
        for r in rows
    ]
