# 🏅 SIMT Kompetisi Explorer

Pipeline lengkap untuk **mengambil, menyimpan, dan menganalisis** data lomba/kompetisi dari portal kuasi resmi Kemendikdasmen — [SIMT (Sistem Informasi Manajemen Talenta)](https://simt.kemendikdasmen.go.id).

Terdiri dari tiga lapisan utama yang bekerja bersama:

```
Scraper  →  SQLite DB  →  FastAPI REST API  →  Streamlit Dashboard
```

---

## 📋 Daftar Isi

- [Fitur Utama](#-fitur-utama)
- [Struktur Proyek](#-struktur-proyek)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Instalasi](#-instalasi)
- [Cara Penggunaan](#-cara-penggunaan)
  - [1. Scraper](#1-scraper)
  - [2. REST API](#2-rest-api)
  - [3. Dashboard](#3-dashboard)
- [API Endpoints](#-api-endpoints)
- [Database Schema](#-database-schema)
- [Tech Stack](#-tech-stack)

---

## ✨ Fitur Utama

| Lapisan | Fitur |
|---|---|
| **Scraper** | Retry otomatis (exponential backoff), resume capability, progress bar, simpan ke SQLite & CSV |
| **REST API** | Pagination, full-text search, multi-filter (level, sektor, cluster, tahun, negara, rating), analytics endpoint |
| **Dashboard** | 5 halaman interaktif: Overview KPI, Analisis Penyelenggara, Peta Geografi, Search & Export, Score Deep-Dive |

---

## 📁 Struktur Proyek

```
scraping data/
│
├── scraper/
│   └── scraper.py          # Web scraper utama (SIMT API)
│
├── api/
│   ├── main.py             # FastAPI app entry point
│   ├── schemas.py          # Pydantic response schemas
│   └── routes/
│       ├── competitions.py # Endpoint: list, search, filter, detail
│       └── analytics.py    # Endpoint: statistik & agregasi
│
├── database/
│   ├── schema.py           # SQLAlchemy ORM models
│   ├── seed.py             # Loader CSV → SQLite
│   └── kompetisi.db        # SQLite database (auto-generated)
│
├── dashboard/
│   └── app.py              # Streamlit dashboard (5 halaman)
│
├── data_kurasi_simt.csv    # Output CSV dari scraper
├── requirements.txt
└── scrap-data-lomba.py     # Scraper versi awal (legacy)
```

---

## 🏗️ Arsitektur Sistem

```
┌─────────────────────────────────────────────────────────────────┐
│                       SIMT Kemendikdasmen                        │
│              https://simt.kemendikdasmen.go.id/api/v2/          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP GET (paginated)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       scraper/scraper.py                         │
│  • Retry logic (3x exponential backoff)                          │
│  • Resume dari halaman terakhir (.scraper_progress.json)         │
│  • Progress bar (tqdm)                                           │
└───────────────┬─────────────────────────┬───────────────────────┘
                │                         │
                ▼                         ▼
    database/kompetisi.db        data_kurasi_simt.csv
      (SQLite via ORM)              (flat file backup)
                │
                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   api/main.py  (FastAPI)                         │
│  GET /api/competitions     — list + filter + pagination          │
│  GET /api/competitions/search — full-text search                 │
│  GET /api/competitions/{id}   — detail per lomba                 │
│  GET /api/analytics/overview  — KPI stats                        │
│  GET /api/analytics/by-sector — breakdown per sektor             │
│  GET /api/analytics/...       — organizer, geography, score      │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP (httpx)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               dashboard/app.py  (Streamlit)                      │
│  📊 Overview          — KPI cards + distribusi charts            │
│  🏆 Organizer Quality — Scatter plot + "pabrik lomba" analysis   │
│  🗺  Geography         — Breakdown negara + peta                 │
│  🔍 Search & Filter   — Pencarian interaktif + export CSV        │
│  📈 Score Deep-Dive   — Distribusi skor, threshold, batch trend  │
└─────────────────────────────────────────────────────────────────┘
```

---

## ⚙️ Instalasi

**Prasyarat:** Python 3.10+

```bash
# 1. Clone repo
git clone https://github.com/rab781/data-lomba.git
cd data-lomba

# 2. Buat virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 Cara Penggunaan

### 1. Scraper

Ambil data dari SIMT API dan simpan ke SQLite + CSV:

```bash
# Jalankan scraper (dengan resume otomatis)
python scraper/scraper.py

# Paksa mulai dari halaman 1 (abaikan progress lama)
python scraper/scraper.py --fresh

# Juga simpan sebagai CSV
python scraper/scraper.py --output-csv
```

> Scraper akan menyimpan progress ke `.scraper_progress.json` sehingga aman jika terputus di tengah jalan.

---

### 2. REST API

Jalankan FastAPI server:

```bash
uvicorn api.main:app --reload --port 8000
```

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **Health check:** [http://localhost:8000/health](http://localhost:8000/health)

---

### 3. Dashboard

> Pastikan FastAPI server sudah berjalan sebelum membuka dashboard.

```bash
streamlit run dashboard/app.py
```

Dashboard akan terbuka di [http://localhost:8501](http://localhost:8501).

---

## 📡 API Endpoints

### Competitions

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/api/competitions` | List semua kompetisi (pagination + filter) |
| `GET` | `/api/competitions/search?q=<keyword>` | Full-text search |
| `GET` | `/api/competitions/{id}` | Detail satu kompetisi |

**Query params filter untuk `/api/competitions`:**

| Parameter | Tipe | Contoh |
|---|---|---|
| `page` | int | `1` |
| `per_page` | int (max 100) | `20` |
| `sort_by` | `score` / `rating` / `id` | `score` |
| `order` | `asc` / `desc` | `desc` |
| `level` | string | `Internasional` |
| `sector` | string | `Teknologi` |
| `cluster` | string | `AI` |
| `type` | string | `Individu` |
| `rating_min` | int (0–5) | `3` |
| `rating_max` | int (0–5) | `5` |
| `country_code` | string | `ID` |
| `year_start` | int | `2022` |
| `year_end` | int | `2024` |

### Analytics

| Method | Endpoint | Deskripsi |
|---|---|---|
| `GET` | `/api/analytics/overview` | KPI global (total, avg score, distribusi) |
| `GET` | `/api/analytics/by-sector` | Breakdown per sektor |
| `GET` | `/api/analytics/organizers` | Ringkasan penyelenggara |
| `GET` | `/api/analytics/geography` | Breakdown per negara |
| `GET` | `/api/analytics/score-buckets` | Distribusi bucket skor |
| `GET` | `/api/analytics/batch-trend` | Tren jumlah lomba per batch/tahun |

---

## 🗄️ Database Schema

Database SQLite (`database/kompetisi.db`) terdiri dari 3 tabel yang dinormalisasi:

```
organizers
├── id (PK, UUID)
├── name
├── short_name
└── useful_link

competition_events
├── id (PK, UUID)
├── name / short_name
├── competition_start / competition_end
├── country / country_code
└── useful_link

competitions
├── id (PK, int)
├── branch_id / branch
├── competition_id (FK → competition_events)
├── organizer_id   (FK → organizers)
├── category / level / type / sector / cluster
├── score / rating
└── batch_raw / batch_num / batch_year
```

---

## 🛠️ Tech Stack

| Komponen | Library |
|---|---|
| Scraping | `requests`, `tqdm` |
| Database | `SQLAlchemy` 2.0 + SQLite |
| REST API | `FastAPI`, `uvicorn`, `pydantic` |
| Dashboard | `Streamlit`, `Plotly`, `httpx` |
| Data | `pandas` |

---

## 📄 Lisensi

Data bersumber dari portal publik [SIMT Kemendikdasmen](https://simt.kemendikdasmen.go.id). Proyek ini dibuat untuk keperluan riset dan analisis data pendidikan.
