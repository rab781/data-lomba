"""
FastAPI main application.

Run with:
    uvicorn api.main:app --reload --port 8000
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.schema import init_db
from api.routes.competitions import router as comp_router
from api.routes.analytics    import router as analytics_router

# ── App setup ────────────────────────────────────
app = FastAPI(
    title       = "SIMT Kompetisi API",
    description = (
        "REST API for exploring 4.981+ curated competitions from "
        "SIMT Kemendikdasmen. Provides search, filtering, and "
        "analytics endpoints.\n\n"
        "**Data Source:** https://simt.kemendikdasmen.go.id"
    ),
    version     = "1.0.0",
    docs_url    = "/docs",
    redoc_url   = "/redoc",
)

# Allow Streamlit dashboard to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routes ───────────────────────────────────────
app.include_router(comp_router,     prefix="/api")
app.include_router(analytics_router, prefix="/api")


# ── Startup ──────────────────────────────────────
@app.on_event("startup")
def startup():
    init_db()


# ── Health check ─────────────────────────────────
@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "message": "SIMT Kompetisi API is running 🚀"}

@app.get("/health", tags=["health"])
def health():
    from database.schema import SessionLocal, Competition
    db = SessionLocal()
    count = db.query(Competition).count()
    db.close()
    return {"status": "ok", "competition_count": count}
