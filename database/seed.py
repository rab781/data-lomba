"""
Seed script: Load & clean data_kurasi_simt.csv → SQLite database.

Run from project root:
    python database/seed.py

Steps:
    1. Read CSV
    2. Drop dead columns
    3. Parse & normalize fields
    4. Populate Organizers, CompetitionEvents, Competitions tables
"""
import sys
import re
import pandas as pd
from pathlib import Path
from datetime import datetime

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.schema import (
    init_db, SessionLocal,
    Organizer, CompetitionEvent, Competition
)

CSV_PATH = Path(__file__).parent.parent / "data_kurasi_simt.csv"

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def parse_datetime(val):
    if pd.isna(val) or val == "":
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val).strip(), fmt)
        except ValueError:
            continue
    return None


def parse_batch(raw: str):
    """
    Extracts (batch_num, batch_year) from inconsistent batch strings.
    Examples:
        'Batch 1'                       → (1, None)
        'Batch 7/2025 Kurasi Cabang'    → (7, 2025)
        'Batch 4/2024 Kurasi Cabang Ajang' → (4, 2024)
    """
    if not raw or pd.isna(raw):
        return None, None
    raw = str(raw).strip()
    # Try "Batch N/YYYY ..."
    match = re.search(r"[Bb]atch\s+(\d+)/(\d{4})", raw)
    if match:
        return int(match.group(1)), int(match.group(2))
    # Try "Batch N"
    match = re.search(r"[Bb]atch\s+(\d+)", raw)
    if match:
        return int(match.group(1)), None
    return None, None


# ──────────────────────────────────────────────
# Main seed logic
# ──────────────────────────────────────────────

def seed():
    print("=" * 60)
    print("SIMT Kompetisi — Database Seed")
    print("=" * 60)

    # 1. Init tables
    print("\n[1/5] Initializing database schema...")
    init_db()
    print("      OK — tables created/verified.")

    # 2. Load CSV
    print(f"\n[2/5] Loading CSV: {CSV_PATH.name} ...")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"      Loaded {len(df):,} rows × {len(df.columns)} columns.")

    # 3. Drop dead / zero-information columns
    DEAD_COLS = ["description", "instrument", "created_by", "isEvent"]
    df = df.drop(columns=[c for c in DEAD_COLS if c in df.columns])
    print(f"\n[3/5] Dropped {len(DEAD_COLS)} dead columns: {DEAD_COLS}")

    # Parse datetimes
    for col in ["competition_start", "competition_end", "created_at", "updated_at"]:
        df[col] = df[col].apply(parse_datetime)

    # Parse batch
    df[["batch_num", "batch_year"]] = df["batch"].apply(
        lambda x: pd.Series(parse_batch(x))
    )

    # Clean nulls for string fields
    for col in ["short_name_of_organizer", "short_name_of_competition", "country", "country_code"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    print("      Datetime & batch fields parsed.")

    # 4. Populate DB
    db = SessionLocal()
    try:
        # ── Organizers (deduplicate by organizer_id) ──
        print("\n[4/5] Seeding organizers...")
        org_df = df[["organizer_id", "organizer", "short_name_of_organizer", "organizer_useful_link"]].drop_duplicates("organizer_id")
        org_count = 0
        for _, row in org_df.iterrows():
            existing = db.get(Organizer, str(row["organizer_id"]))
            if not existing:
                db.add(Organizer(
                    id          = str(row["organizer_id"]),
                    name        = str(row["organizer"]),
                    short_name  = str(row["short_name_of_organizer"]) or None,
                    useful_link = str(row["organizer_useful_link"]) if pd.notna(row["organizer_useful_link"]) else None,
                ))
                org_count += 1
        db.commit()
        print(f"      Inserted {org_count:,} organizers ({len(org_df):,} unique).")

        # ── Competition Events (deduplicate by competition_id) ──
        print("\n      Seeding competition events...")
        evt_df = df[[
            "competition_id", "competition", "short_name_of_competition",
            "competition_start", "competition_end", "country", "country_code",
            "competition_useful_link"
        ]].drop_duplicates("competition_id")
        evt_count = 0
        for _, row in evt_df.iterrows():
            existing = db.get(CompetitionEvent, str(row["competition_id"]))
            if not existing:
                db.add(CompetitionEvent(
                    id                = str(row["competition_id"]),
                    name              = str(row["competition"]),
                    short_name        = str(row["short_name_of_competition"]) or None,
                    competition_start = row["competition_start"],
                    competition_end   = row["competition_end"],
                    country           = str(row["country"]) or None,
                    country_code      = str(row["country_code"]) or None,
                    useful_link       = str(row["competition_useful_link"]) if pd.notna(row["competition_useful_link"]) else None,
                ))
                evt_count += 1
        db.commit()
        print(f"      Inserted {evt_count:,} competition events ({len(evt_df):,} unique).")

        # ── Competition branches (all rows) ──
        print("\n      Seeding competition branches...")
        # Clear existing to allow re-seed
        db.query(Competition).delete()
        db.commit()

        batch_size = 500
        total = len(df)
        inserted = 0
        for start in range(0, total, batch_size):
            chunk = df.iloc[start : start + batch_size]
            for _, row in chunk.iterrows():
                db.add(Competition(
                    id             = int(row["id"]),
                    branch_id      = int(row["branch_id"]) if pd.notna(row["branch_id"]) else None,
                    branch         = str(row["branch"]),
                    competition_id = str(row["competition_id"]),
                    organizer_id   = str(row["organizer_id"]),
                    category       = str(row["category"]) if pd.notna(row["category"]) else None,
                    level          = str(row["level"]) if pd.notna(row["level"]) else None,
                    type           = str(row["type"]) if pd.notna(row["type"]) else None,
                    sector         = str(row["sector"]) if pd.notna(row["sector"]) else None,
                    cluster        = str(row["cluster"]) if pd.notna(row["cluster"]) else None,
                    score          = float(row["score"]) if pd.notna(row["score"]) else None,
                    rating         = int(row["rating"]) if pd.notna(row["rating"]) else None,
                    batch_raw      = str(row["batch"]) if pd.notna(row["batch"]) else None,
                    batch_num      = int(row["batch_num"]) if pd.notna(row["batch_num"]) else None,
                    batch_year     = int(row["batch_year"]) if pd.notna(row["batch_year"]) else None,
                    created_at     = row["created_at"],
                    updated_at     = row["updated_at"],
                ))
                inserted += 1
            db.commit()
            print(f"      Progress: {min(start + batch_size, total):,}/{total:,}", end="\r")

        print(f"\n      Inserted {inserted:,} competition branches.")

        # ── Summary ──
        print("\n[5/5] Verification:")
        print(f"      Organizers        : {db.query(Organizer).count():>6,}")
        print(f"      Competition Events: {db.query(CompetitionEvent).count():>6,}")
        print(f"      Competition Branches: {db.query(Competition).count():>4,}")

        print("\n✅  Database seeded successfully!")
        print(f"   📂 Location: {(Path(__file__).parent / 'kompetisi.db').resolve()}\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌  Error during seeding: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
