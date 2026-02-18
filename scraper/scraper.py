"""
Improved SIMT Kompetisi Scraper
─────────────────────────────
Improvements over original scrap-data-lomba.py:
  - Retry logic (3x with exponential backoff)
  - Resume capability (saves last page to .progress file)
  - Saves directly to SQLite (via seed logic) AND CSV
  - Progress bar (tqdm)
  - Structured logging

Usage:
    python scraper/scraper.py
    python scraper/scraper.py --output-csv   # also save as CSV
    python scraper/scraper.py --fresh        # ignore resume, start from page 1
"""
import sys
import time
import json
import logging
import argparse
import requests
import pandas as pd
from pathlib import Path
from tqdm import tqdm

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
BASE_URL   = "https://simt.kemendikdasmen.go.id/api/v2/list-kurasi"
PAGE_SIZE  = 10
DELAY_SEC  = 2
MAX_RETRY  = 3
TIMEOUT    = 15

ROOT_DIR      = Path(__file__).parent.parent
CSV_PATH      = ROOT_DIR / "data_kurasi_simt.csv"
PROGRESS_FILE = ROOT_DIR / ".scraper_progress.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("simt-scraper")


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def fetch_page(page: int) -> dict | None:
    """Fetch one page from the API with retry logic."""
    params = {"page": page, "per_page": PAGE_SIZE}
    for attempt in range(1, MAX_RETRY + 1):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            wait = 2 ** attempt
            log.warning(f"Page {page} attempt {attempt}/{MAX_RETRY} failed: {e}. Retrying in {wait}s...")
            if attempt == MAX_RETRY:
                raise
            time.sleep(wait)


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {"last_page": 0, "total_page": None, "collected": 0}


def save_progress(data: dict):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)


def clear_progress():
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()


# ──────────────────────────────────────────────
# Main scraper
# ──────────────────────────────────────────────

def scrape(fresh: bool = False, save_csv: bool = True):
    log.info("Starting SIMT scraper...")

    progress = {"last_page": 0, "total_page": None, "collected": 0}
    all_items: list[dict] = []

    # Load existing CSV for resume
    if not fresh and PROGRESS_FILE.exists():
        progress = load_progress()
        start_page = progress["last_page"] + 1
        log.info(f"Resuming from page {start_page} (collected {progress['collected']:,} items so far).")
        if CSV_PATH.exists() and progress["collected"] > 0:
            existing_df = pd.read_csv(CSV_PATH)
            all_items = existing_df.to_dict("records")
            log.info(f"Loaded {len(all_items):,} existing records from CSV.")
    else:
        if fresh:
            clear_progress()
            log.info("Fresh run — ignoring previous progress.")
        start_page = 1

    # First request to get total pages
    log.info(f"Fetching page {start_page} to get total page count...")
    first_data = fetch_page(start_page)
    if first_data is None:
        log.error("Failed to fetch first page. Aborting.")
        return
    total_page = first_data.get("total_page", 1)
    progress["total_page"] = total_page
    log.info(f"Total pages: {total_page}")

    # Extract items from first page
    items = first_data.get("data", [])
    if isinstance(items, dict):
        items = items.get("data", [])
    all_items.extend(items)

    # Paginate through remaining pages
    pbar = tqdm(
        range(start_page + 1, total_page + 1),
        desc="Scraping pages",
        unit="page",
        initial=start_page - 1,
        total=total_page,
    )

    for page in pbar:
        time.sleep(DELAY_SEC)
        try:
            data = fetch_page(page)
            if data is None:
                log.warning(f"Skipping page {page} — no data returned.")
                continue
            items = data.get("data", [])
            if isinstance(items, dict):
                items = items.get("data", [])
            all_items.extend(items)

            progress["last_page"] = page
            progress["collected"] = len(all_items)
            save_progress(progress)

            pbar.set_postfix({"collected": len(all_items)})
        except Exception as e:
            log.error(f"Failed to fetch page {page}: {e}")
            log.info(f"Progress saved at page {page - 1}. Run again to resume.")
            break

    log.info(f"\nScraping done. Total items collected: {len(all_items):,}")

    if not all_items:
        log.warning("No data collected. Exiting.")
        return

    # Save to CSV
    if save_csv:
        df = pd.DataFrame(all_items)
        df.to_csv(CSV_PATH, index=False)
        log.info(f"Saved {len(df):,} rows to {CSV_PATH}")

    # Seed to SQLite
    log.info("Seeding data into SQLite database...")
    sys.path.insert(0, str(ROOT_DIR))
    from database.seed import seed as run_seed
    run_seed()

    clear_progress()
    log.info("✅ Scraping and seeding complete!")


# ──────────────────────────────────────────────
# CLI entry point
# ──────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SIMT Kompetisi Scraper")
    parser.add_argument("--fresh",       action="store_true", help="Start from page 1, ignore resume")
    parser.add_argument("--output-csv",  action="store_true", default=True, help="Save output as CSV (default: True)")
    parser.add_argument("--no-csv",      action="store_true", help="Skip CSV output")
    args = parser.parse_args()

    scrape(fresh=args.fresh, save_csv=not args.no_csv)
