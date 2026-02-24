"""
SIMT Kompetisi Explorer — Streamlit Dashboard
Redesigned with Stitch UI design system.
═══════════════════════════════════════════════

5 Pages:
  1. 📊 Overview          — KPI cards + distribution charts
  2. 🏆 Organizer Quality — Scatter plot + "pabrik lomba" analysis
  3. 🗺  Geography         — Country breakdown + map
  4. 🔍 Search & Export   — Interactive search + export
  5. 📈 Score Deep-Dive   — Distribution, thresholds, batch trend

Run:
    streamlit run dashboard/app.py
"""
import sys
import json
import math
import os
from pathlib import Path
from typing import Any, Generator

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import httpx
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Config ────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title="SIMT Kompetisi Explorer",
    page_icon="🏅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Inject fonts & global CSS (Stitch design system) ─────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@300;400;500;600;700;900&display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet"/>

<style>
/* ── Base ── */
:root {
    --primary: #137fec;
    --primary-10: rgba(19,127,236,0.10);
    --bg: #101922;
    --bg-card: #1a2027;
    --bg-sidebar: #111418;
    --bg-input: #1c2127;
    --border: rgba(255,255,255,0.08);
    --text: #f0f4f8;
    --text-muted: #8a9bb0;
    --success: #10b981;
    --danger: #ef4444;
    --amber: #f59e0b;
}

html, body, [class*="css"] {
    font-family: 'Public Sans', sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-sidebar) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text-muted) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: var(--text) !important; }

/* ── Main area ── */
[data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
}
[data-testid="block-container"] {
    background: var(--bg) !important;
    padding-top: 1.5rem !important;
}

/* ── Titles ── */
h1 { font-weight: 900 !important; letter-spacing: -0.5px !important; color: var(--text) !important; }
h2, h3 { font-weight: 700 !important; color: var(--text) !important; }
p, span, div { color: var(--text-muted); }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Metric widget ── */
[data-testid="metric-container"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 1.25rem 1.5rem !important;
}
[data-testid="stMetricValue"] { color: var(--text) !important; font-weight: 700 !important; font-size: 1.75rem !important; }
[data-testid="stMetricLabel"] { color: var(--text-muted) !important; font-size: 0.8rem !important; font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricDelta"] { font-size: 0.75rem !important; }

/* ── KPI Hero cards ── */
.kpi-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.35rem 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
}
.kpi-card .kpi-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.kpi-card .kpi-label {
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    color: var(--text-muted);
}
.kpi-card .kpi-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 34px; height: 34px;
    border-radius: 8px;
    font-size: 18px;
}
.kpi-card .kpi-value {
    font-size: 2rem;
    font-weight: 900;
    color: var(--text);
    line-height: 1;
    margin-top: 0.5rem;
}
.kpi-card .kpi-badge {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 7px;
    border-radius: 99px;
    margin-top: 4px;
}
.kpi-badge-up   { background: rgba(16,185,129,0.15); color: #10b981; }
.kpi-badge-down { background: rgba(239,68,68,0.15);  color: #ef4444; }
.kpi-badge-neu  { background: rgba(138,155,176,0.15); color: #8a9bb0; }

/* ── Section card wrapper ── */
.section-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    margin-bottom: 1.25rem;
}
.section-card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text);
    margin-bottom: 0.25rem;
}
.section-card-subtitle {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
}

/* ── Page header ── */
.page-header { margin-bottom: 1.5rem; }
.page-header h1 { font-size: 2rem; font-weight: 900; color: var(--text); margin-bottom: 0.2rem; }
.page-header p  { font-size: 0.9rem; color: var(--text-muted); margin: 0; }

/* ── Level badge ── */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 700;
    white-space: nowrap;
}
.badge-intl     { background: rgba(168,85,247,0.15);  color: #c084fc; }
.badge-national { background: rgba(19,127,236,0.15);  color: #60a5fa; }
.badge-region   { background: rgba(16,185,129,0.15);  color: #34d399; }
.badge-local    { background: rgba(245,158,11,0.15);  color: #fbbf24; }
.badge-flagged  { background: rgba(239,68,68,0.15);   color: #f87171; }
.badge-ok       { background: rgba(16,185,129,0.15);  color: #34d399; }

/* ── Dataframe / Table ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    overflow: hidden;
}
.dvn-scroller { background: var(--bg-card) !important; }

/* ── Inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"],
[data-testid="stSlider"] {
    background: var(--bg-input) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--primary) !important;
    color: white !important;
    border: none !important;
    font-weight: 700 !important;
    border-radius: 10px !important;
    transition: opacity .15s;
}
.stButton > button:hover { opacity: 0.88; }
.stButton > button[disabled] {
    background: var(--bg-card) !important;
    color: var(--text-muted) !important;
    opacity: 0.6 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
[data-testid="stExpanderDetails"] { background: var(--bg-card) !important; }

/* ── Alert boxes ── */
[data-testid="stAlert"] { border-radius: 10px !important; }

/* ── Plotly chart background ── */
.js-plotly-plot .plotly { background: transparent !important; }
.main-svg { background: transparent !important; }

/* ── Radio sidebar nav ── */
[data-testid="stRadio"] label {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    padding: 8px 14px !important;
    border-radius: 10px !important;
    transition: background .15s !important;
    font-weight: 500 !important;
    font-size: 0.9rem !important;
    cursor: pointer;
}
[data-testid="stRadio"] label:hover { background: rgba(255,255,255,0.05) !important; }

/* ── Result chip ── */
.result-chip {
    display: inline-block;
    background: var(--primary-10);
    color: var(--primary);
    padding: 2px 12px;
    border-radius: 99px;
    font-size: 0.82rem;
    font-weight: 700;
}

/* ── API status chip ── */
.api-ok   { display:flex;align-items:center;gap:8px;background:rgba(16,185,129,0.1);
            padding:10px 14px;border-radius:10px;border:1px solid rgba(16,185,129,0.2); }
.api-err  { background:rgba(239,68,68,0.1);padding:10px 14px;border-radius:10px;
            border:1px solid rgba(239,68,68,0.2); }

/* ── Chatbot ── */
.chat-wrap {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
}
.chat-bubble {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    max-width: 85%;
}
.chat-bubble.user  { margin-left: auto; flex-direction: row-reverse; }
.chat-avatar {
    width: 34px; height: 34px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px; flex-shrink: 0;
}
.avatar-user { background: rgba(19,127,236,0.2); }
.avatar-ai   { background: rgba(168,85,247,0.2); }
.chat-text {
    padding: 10px 14px;
    border-radius: 14px;
    font-size: 0.88rem;
    line-height: 1.55;
    color: #f0f4f8;
    white-space: pre-wrap;
    word-break: break-word;
}
.chat-text-user { background: rgba(19,127,236,0.18); border: 1px solid rgba(19,127,236,0.25); }
.chat-text-ai   { background: var(--bg-card);        border: 1px solid var(--border); }
.chat-thinking {
    display: flex;
    gap: 4px;
    align-items: center;
    padding: 10px 14px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 14px;
}
.chat-thinking span {
    width: 7px; height: 7px; border-radius: 50%;
    background: #8a9bb0;
    animation: bounce 1.2s infinite;
    display: inline-block;
}
.chat-thinking span:nth-child(2) { animation-delay: .2s; }
.chat-thinking span:nth-child(3) { animation-delay: .4s; }
@keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: .4; }
    40%           { transform: translateY(-6px); opacity: 1; }
}
.chat-meta {
    font-size: 0.7rem;
    color: #4a5568;
    margin-top: 3px;
    padding: 0 2px;
}
.suggested-btn {
    display: inline-block;
    background: var(--primary-10);
    color: var(--primary);
    border: 1px solid rgba(19,127,236,0.25);
    border-radius: 20px;
    padding: 5px 14px;
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition: background .15s;
    white-space: nowrap;
}
.suggested-btn:hover { background: rgba(19,127,236,0.2); }
</style>
""", unsafe_allow_html=True)

# ── Chutes LLM config ───────────────────────────────────────────
CHUTES_TOKEN = os.getenv("CHUTES_API_TOKEN", "")
CHUTES_URL   = "https://llm.chutes.ai/v1/chat/completions"
CHUTES_MODEL = "deepseek-ai/DeepSeek-V3-0324-TEE"

SIMT_SYSTEM_PROMPT = """\
Kamu adalah AI Assistant untuk SIMT Kompetisi Explorer, platform analitik data lomba/kompetisi
resmi dari Kemendikdasmen (Kementerian Pendidikan Dasar dan Menengah) Indonesia.

Database berisi 4.981+ kompetisi yang dikurasi, mencakup:
- Level: Lokal, Provinsi, Nasional, Internasional
- Sektor: Matematika, Sains, Teknologi, Seni, Olahraga, dll.
- Skor kualitatif (0-100) dan Rating bintang (1-5)
- Data penyelenggara dan lokasi negara

Tugasmu:
1. Membantu pengguna memahami data kompetisi Indonesia
2. Memberikan saran lomba yang relevan berdasarkan minat/jenjang
3. Menjelaskan insight dari data (tren, distribusi, kualitas penyelenggara)
4. Menjawab pertanyaan tentang sistem penilaian SIMT
5. Berbahasa Indonesia atau Inggris sesuai pertanyaan pengguna

Jawab secara ringkas, informatif, dan pada poin yang ditanya.
"""


def stream_chutes(
    messages: list[dict],
    token: str,
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> Generator[str, None, None]:
    """Synchronous SSE streaming generator for Chutes LLM API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    body = {
        "model": CHUTES_MODEL,
        "messages": messages,
        "stream": True,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    with httpx.stream("POST", CHUTES_URL, headers=headers, json=body, timeout=60) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.startswith("data: "):
                continue
            data = line[6:]
            if data == "[DONE]":
                break
            try:
                chunk  = json.loads(data)
                delta  = chunk["choices"][0]["delta"].get("content", "")
                if delta:
                    yield delta
            except Exception:
                pass


# ── Plotly dark theme ─────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Public Sans", color="#8a9bb0"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", linecolor="rgba(255,255,255,0.1)"),
    margin=dict(t=30, b=30, l=10, r=10),
)
PLOTLY_COLORS = ["#137fec", "#a855f7", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#ec4899"]


def apply_theme(fig, height: int = 380):
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


# ── API helpers ───────────────────────────────────────────────────
@st.cache_data(ttl=300)
def api_get(path: str, params: dict[str, Any] | None = None) -> Any:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API Error ({path}): {e}")
        return None


def check_api():
    try:
        r = httpx.get("http://localhost:8000/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ── HTML component helpers ────────────────────────────────────────
def kpi_card(label: str, value: str, icon: str, icon_bg: str,
             badge_text: str = "", badge_type: str = "neu") -> str:
    badge_html = ""
    if badge_text:
        badge_html = f"<span class='kpi-badge kpi-badge-{badge_type}'>{badge_text}</span>"
    return f"""
    <div class="kpi-card">
        <div class="kpi-head">
            <span class="kpi-label">{label}</span>
            <span class="kpi-icon" style="background:{icon_bg};">{icon}</span>
        </div>
        <div class="kpi-value">{value}</div>
        {badge_html}
    </div>"""


# ── Sidebar navigation ────────────────────────────────────────────
PAGES = {
    "📊  Overview":          "overview",
    "🏆  Organizer Quality": "organizer",
    "🗺️  Geography":         "geography",
    "🔍  Search & Export":   "search",
    "📈  Score Deep-Dive":   "score",
    "🤖  AI Assistant":      "chatbot",
}

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:12px;padding:4px 0 16px;">
        <div style="width:40px;height:40px;background:linear-gradient(135deg,#137fec,#6366f1);
                    border-radius:10px;display:flex;align-items:center;justify-content:center;
                    font-size:20px;flex-shrink:0;">🏅</div>
        <div>
            <div style="font-size:1rem;font-weight:800;color:#f0f4f8;line-height:1.2;">SIMT Explorer</div>
            <div style="font-size:0.72rem;color:#8a9bb0;">Competition Analytics</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        "<p style='font-size:0.68rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.1em;color:#4a5568;padding:0 4px 6px;'>Navigation</p>",
        unsafe_allow_html=True,
    )
    page   = st.radio("nav", list(PAGES.keys()), label_visibility="collapsed")
    active = PAGES[page]

    st.divider()

    if check_api():
        st.markdown("""
        <div class="api-ok">
            <div style="width:8px;height:8px;border-radius:50%;background:#10b981;flex-shrink:0;"></div>
            <span style="font-size:0.8rem;font-weight:600;color:#10b981;">API Connected</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="api-err">
            <div style="font-size:0.8rem;font-weight:600;color:#ef4444;margin-bottom:4px;">⚠ API Offline</div>
            <div style="font-size:0.72rem;color:#8a9bb0;">Run: uvicorn api.main:app --reload</div>
        </div>
        """, unsafe_allow_html=True)
        st.stop()


# ════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ════════════════════════════════════════════════════════════════
if active == "overview":
    st.markdown("""
    <div class='page-header'>
        <h1>Dashboard Overview</h1>
        <p>Gambaran menyeluruh ekosistem kompetisi yang dikurasi Kemendikdasmen.</p>
    </div>
    """, unsafe_allow_html=True)

    data = api_get("/analytics/overview")
    if not data:
        st.stop()

    # ── KPI Cards ───────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    cards = [
        (c1, "Total Lomba",   f"{data['total_competitions']:,}", "🏆", "rgba(19,127,236,0.15)"),
        (c2, "Event Unik",    f"{data['total_events']:,}",       "📅", "rgba(168,85,247,0.15)"),
        (c3, "Penyelenggara", f"{data['total_organizers']:,}",   "🏢", "rgba(245,158,11,0.15)"),
        (c4, "Negara",        f"{data['total_countries']:,}",    "🌍", "rgba(16,185,129,0.15)"),
        (c5, "Avg Score",     f"{data['avg_score']:.2f}",        "📊", "rgba(239,68,68,0.15)"),
    ]
    for col, label, value, icon, bg in cards:
        col.markdown(kpi_card(label, value, icon, bg), unsafe_allow_html=True)

    st.markdown("<div style='height:1.5rem'></div>", unsafe_allow_html=True)

    # ── Row 1: Level bar + Cluster donut ────────────────────────
    left, right = st.columns(2)

    with left:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Competitions by Level</div>"
            "<div class='section-card-subtitle'>Distribution across competition tiers</div>",
            unsafe_allow_html=True,
        )
        level_df = pd.DataFrame(data["level_distribution"])
        fig = px.bar(
            level_df, x="count", y="label", orientation="h",
            color="avg_score",
            color_continuous_scale=["#1d3557", "#137fec", "#60efff"],
            text="count",
            labels={"label": "", "count": "Jumlah", "avg_score": "Avg Score"},
        )
        fig.update_traces(textposition="outside", textfont_color="#f0f4f8", marker_line_width=0)
        apply_theme(fig, 320)
        fig.update_coloraxes(colorbar_tickfont_color="#8a9bb0", colorbar_title_font_color="#8a9bb0")
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Distribusi per Cluster</div>"
            "<div class='section-card-subtitle'>Proporsi setiap kluster kompetisi</div>",
            unsafe_allow_html=True,
        )
        cluster_df = pd.DataFrame(data["cluster_distribution"])
        fig = px.pie(
            cluster_df, values="count", names="label",
            color_discrete_sequence=PLOTLY_COLORS, hole=0.44,
        )
        fig.update_traces(
            textposition="outside", textinfo="percent+label",
            outsidetextfont_color="#8a9bb0",
            marker_line=dict(color="#101922", width=2),
        )
        apply_theme(fig, 320)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 2: Top Sectors ───────────────────────────────────────
    sector_data = api_get("/analytics/by-sector")
    if sector_data:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Top Sektor Kompetisi</div>"
            "<div class='section-card-subtitle'>Jumlah lomba per bidang — warna: rata-rata skor</div>",
            unsafe_allow_html=True,
        )
        sector_df = pd.DataFrame(sector_data).sort_values("count", ascending=True)
        fig = px.bar(
            sector_df, x="count", y="sector", orientation="h",
            color="avg_score",
            color_continuous_scale=["#1d3557", "#137fec", "#10b981"],
            text="count",
            labels={"sector": "", "count": "Jumlah", "avg_score": "Avg Score"},
        )
        fig.update_traces(textposition="outside", textfont_color="#f0f4f8", marker_line_width=0)
        apply_theme(fig, 430)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 3: Growth Trend ──────────────────────────────────────
    year_data = api_get("/analytics/by-year")
    if year_data:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Growth Trends</div>"
            "<div class='section-card-subtitle'>Volume kompetisi dari tahun ke tahun</div>",
            unsafe_allow_html=True,
        )
        year_df = pd.DataFrame(year_data).dropna(subset=["year"])
        year_df["year"] = year_df["year"].astype(str)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=year_df["year"], y=year_df["count"],
            marker_color="rgba(19,127,236,0.18)",
            marker_line_width=0, name="Volume",
        ))
        fig.add_trace(go.Scatter(
            x=year_df["year"], y=year_df["count"],
            mode="lines+markers",
            line=dict(color="#137fec", width=3),
            marker=dict(color="#137fec", size=7, line=dict(color="#101922", width=2)),
            name="Tren",
        ))
        apply_theme(fig, 320)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Row 4: Individu vs Kelompok ──────────────────────────────
    type_df = pd.DataFrame(data.get("type_distribution", []))
    if not type_df.empty:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Individu vs Kelompok</div>",
            unsafe_allow_html=True,
        )
        fig = px.pie(
            type_df, values="count", names="label",
            color_discrete_sequence=["#137fec", "#a855f7"], hole=0.5,
        )
        fig.update_traces(
            textposition="outside", textinfo="percent+label",
            outsidetextfont_color="#8a9bb0",
            marker_line=dict(color="#101922", width=2),
        )
        apply_theme(fig, 260)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# PAGE 2: ORGANIZER QUALITY
# ════════════════════════════════════════════════════════════════
elif active == "organizer":
    st.markdown("""
    <div class='page-header'>
        <h1>Organizer &amp; Score Analysis</h1>
        <p>Deep dive ke reputasi penyelenggara — dari organizer terpercaya hingga "pabrik lomba".</p>
    </div>
    """, unsafe_allow_html=True)

    org_data = api_get("/analytics/organizer-quality")
    if not org_data:
        st.stop()

    df     = pd.DataFrame(org_data)
    pabrik = df[df["is_flagged"] == True]
    avg_q  = df["avg_score"].mean()

    # ── KPI Cards ───────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(kpi_card("Total Organizers",   f"{len(df):,}",    "🏢", "rgba(19,127,236,0.15)"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Flagged Organizers", f"{len(pabrik):,}", "🚩", "rgba(239,68,68,0.15)", "pabrik lomba", "down"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Avg Score",          f"{avg_q:.1f}" if avg_q else "—", "📊", "rgba(16,185,129,0.15)"), unsafe_allow_html=True)
    c4.markdown(kpi_card("Volume ≥10",         f"{len(df[df['count'] >= 10]):,}", "📈", "rgba(245,158,11,0.15)"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

    # ── Scatter plot ─────────────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("""
    <div class='section-card-title'>Volume vs Quality Scatter</div>
    <div class='section-card-subtitle'>
        Kiri-bawah = banyak lomba tapi skor rendah
        (<b style='color:#ef4444'>pabrik lomba</b>).
        Kanan-atas = organizer berkualitas.
    </div>
    """, unsafe_allow_html=True)

    df["color"] = df["is_flagged"].map({True: "🚩 Pabrik Lomba", False: "✅ Normal"})
    fig = px.scatter(
        df, x="count", y="avg_score",
        color="color",
        color_discrete_map={"🚩 Pabrik Lomba": "#ef4444", "✅ Normal": "#137fec"},
        hover_name="name",
        hover_data={"count": True, "avg_score": ":.2f", "avg_rating": ":.1f", "color": False},
        size="count", size_max=40,
        labels={"count": "Jumlah Lomba", "avg_score": "Rata-rata Skor", "color": "Kategori"},
    )
    fig.add_hline(y=45, line_dash="dot", line_color="rgba(239,68,68,0.4)",
                  annotation_text="Skor 45", annotation_font_color="#ef4444",
                  annotation_font_size=11)
    fig.add_vline(x=20, line_dash="dot", line_color="rgba(239,68,68,0.4)",
                  annotation_text="Vol 20", annotation_font_color="#ef4444",
                  annotation_font_size=11)
    apply_theme(fig, 480)
    fig.update_layout(legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(size=12, color="#8a9bb0"),
    ))
    st.plotly_chart(fig, width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Top vs Flagged tables ─────────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-card-title'>🥇 Top 15 Organizers</div>", unsafe_allow_html=True)
        top15 = df.nlargest(15, "avg_score")[["name", "count", "avg_score", "avg_rating"]].copy()
        top15.columns = ["Penyelenggara", "Jml Lomba", "Avg Score", "Avg Rating"]
        top15["Avg Score"] = top15["Avg Score"].round(2)
        st.dataframe(top15, hide_index=True, width='stretch', height=420)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_r:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-card-title'>🚩 Flagged &ldquo;Pabrik Lomba&rdquo;</div>", unsafe_allow_html=True)
        if len(pabrik):
            show = pabrik[["name", "count", "avg_score", "avg_rating"]].sort_values("count", ascending=False).copy()
            show.columns = ["Penyelenggara", "Jml Lomba", "Avg Score", "Avg Rating"]
            show["Avg Score"] = show["Avg Score"].round(2)
            st.dataframe(show, hide_index=True, width='stretch', height=420)
        else:
            st.info("Tidak ada organizer yang di-flag dengan kriteria saat ini.")
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Level comparison bar ──────────────────────────────────────
    level_scores = api_get("/analytics/by-level")
    if level_scores:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>Score Distribution by Level</div>"
            "<div class='section-card-subtitle'>Rata-rata skor: Internasional vs Nasional vs Regional</div>",
            unsafe_allow_html=True,
        )
        s_df = pd.DataFrame(level_scores)
        fig = px.bar(
            s_df, x="level", y="avg_score",
            error_y=s_df["max_score"] - s_df["avg_score"],
            error_y_minus=s_df["avg_score"] - s_df["min_score"],
            color="level",
            color_discrete_sequence=PLOTLY_COLORS,
            text="avg_score",
            labels={"level": "Level", "avg_score": "Rata-rata Skor"},
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside",
                          textfont_color="#f0f4f8", marker_line_width=0)
        apply_theme(fig, 340)
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# PAGE 3: GEOGRAPHY
# ════════════════════════════════════════════════════════════════
elif active == "geography":
    st.markdown("""
    <div class='page-header'>
        <h1>Geographic Map</h1>
        <p>Distribusi kompetisi berdasarkan negara penyelenggara.</p>
    </div>
    """, unsafe_allow_html=True)

    country_data = api_get("/analytics/by-country")
    if not country_data:
        st.stop()

    df = pd.DataFrame(country_data)
    total_countries = len(df)
    id_count = df[df["country_code"] == "ID"]["count"].sum() if "ID" in df["country_code"].values else 0
    intl_pct = (1 - id_count / df["count"].sum()) * 100

    # ── KPI Cards ───────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.markdown(kpi_card("Total Negara",         f"{total_countries}", "🌍", "rgba(19,127,236,0.15)"), unsafe_allow_html=True)
    c2.markdown(kpi_card("Lomba di Indonesia",   f"{int(id_count):,}", "🇮🇩", "rgba(239,68,68,0.15)"), unsafe_allow_html=True)
    c3.markdown(kpi_card("Lomba Luar Negeri",    f"{intl_pct:.1f}%",   "✈️",  "rgba(16,185,129,0.15)"), unsafe_allow_html=True)

    st.markdown("<div style='height:1.25rem'></div>", unsafe_allow_html=True)

    # ── Choropleth map ────────────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-card-title'>World Map — Sebaran Kompetisi</div>", unsafe_allow_html=True)
    fig = px.choropleth(
        df,
        locations="country_code", color="count",
        hover_name="country",
        hover_data={"count": True, "avg_score": ":.2f", "country_code": False},
        color_continuous_scale=["#1d3557", "#137fec", "#60efff"],
        labels={"count": "Jumlah Lomba"},
    )
    fig.update_layout(**PLOTLY_LAYOUT)  # type: ignore[arg-type]
    fig.update_layout(
        height=430,
        geo=dict(
            showframe=False, showcoastlines=True,
            projection_type="natural earth",
            bgcolor="rgba(0,0,0,0)",
            landcolor="rgba(26,32,39,1)",
            coastlinecolor="rgba(255,255,255,0.15)",
            countrycolor="rgba(255,255,255,0.08)",
            showocean=True, oceancolor="#0d1821",
        ),
        coloraxis_colorbar=dict(
            title="Jumlah Lomba",
            tickfont=dict(color="#8a9bb0"),
            title_font_color="#8a9bb0",
        ),
    )
    st.plotly_chart(fig, width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Top 20 countries bar ──────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-card-title'>Top 20 Negara Penyelenggara</div>", unsafe_allow_html=True)
    top_df = df.nlargest(20, "count").sort_values("count")
    fig = px.bar(
        top_df, x="count", y="country", orientation="h",
        color="avg_score",
        color_continuous_scale=["#1d3557", "#137fec", "#10b981"],
        text="count",
        labels={"count": "Jumlah Lomba", "country": "", "avg_score": "Avg Score"},
    )
    fig.update_traces(textposition="outside", textfont_color="#f0f4f8", marker_line_width=0)
    apply_theme(fig, 500)
    st.plotly_chart(fig, width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("💡 Insight: % 'Internasional' yang digelar di Indonesia"):
        comp_intl_id  = api_get("/competitions", params={"level": "Internasional", "per_page": 1, "country_code": "ID"})
        comp_intl_all = api_get("/competitions", params={"level": "Internasional", "per_page": 1})
        if comp_intl_id and comp_intl_all and comp_intl_all["total"]:
            pct = comp_intl_id["total"] / comp_intl_all["total"] * 100
            st.metric(
                "Lomba Internasional di Indonesia",
                f"{comp_intl_id['total']:,} / {comp_intl_all['total']:,}",
                f"{pct:.1f}% dari total Internasional",
            )


# ════════════════════════════════════════════════════════════════
# PAGE 4: SEARCH & EXPORT
# ════════════════════════════════════════════════════════════════
elif active == "search":
    st.markdown("""
    <div class='page-header'>
        <h1>Competition Search</h1>
        <p>Filter dan ekspor data kompetisi sesuai kebutuhanmu.</p>
    </div>
    """, unsafe_allow_html=True)

    options = api_get("/competitions/filters/options") or {}

    # ── Inline filter panel ──────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown("<div class='section-card-title'>🎛️ Filter</div>", unsafe_allow_html=True)

    f_col1, f_col2 = st.columns(2)
    with f_col1:
        search_q = st.text_input(
            "🔍 Cari nama lomba / penyelenggara",
            placeholder="e.g. Olimpiade, BRIN, Chess...",
        )
    with f_col2:
        f_level = st.selectbox("Level", ["Semua"] + options.get("levels", []))

    f_col3, f_col4, f_col5, f_col6 = st.columns(4)
    with f_col3:
        f_sector  = st.selectbox("Sektor",  ["Semua"] + options.get("sectors",  []))
    with f_col4:
        f_cluster = st.selectbox("Cluster", ["Semua"] + options.get("clusters", []))
    with f_col5:
        f_type    = st.selectbox("Tipe",    ["Semua"] + options.get("types",    []))
    with f_col6:
        f_rating  = st.selectbox("Min Rating ⭐", [0, 1, 2, 3, 4, 5],
                                 format_func=lambda x: f"{x}+" if x > 0 else "Semua")

    f_col7, f_col8, f_col9 = st.columns(3)
    with f_col7:
        year_range = options.get("years", [])
        if year_range:
            f_year = st.select_slider(
                "Tahun", options=year_range,
                value=(year_range[0], year_range[-1]),
            )
        else:
            f_year = None
    with f_col8:
        country_opts    = [f"{c['name']} ({c['code']})" for c in options.get("countries", [])]
        f_country_sel   = st.selectbox("Negara", ["Semua"] + country_opts)
        f_country_code  = None
        if f_country_sel != "Semua":
            f_country_code = f_country_sel.split("(")[-1].rstrip(")")
    with f_col9:
        sort_by = st.selectbox("Urutkan", ["score", "rating", "id"])
        order   = st.radio("Urutan", ["desc", "asc"], horizontal=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Build API params ──────────────────────────────────────────
    per_page = 25
    if "search_page" not in st.session_state:
        st.session_state.search_page = 1

    params: dict = {
        "per_page": per_page,
        "page":     st.session_state.search_page,
        "sort_by":  sort_by,
        "order":    order,
    }
    if f_level   != "Semua": params["level"]   = f_level
    if f_sector  != "Semua": params["sector"]  = f_sector
    if f_cluster != "Semua": params["cluster"] = f_cluster
    if f_type    != "Semua": params["type"]    = f_type
    if f_rating  > 0:        params["rating_min"] = f_rating
    if f_country_code:       params["country_code"] = f_country_code
    if f_year and year_range:
        params["year_start"] = f_year[0]
        params["year_end"]   = f_year[1]

    if search_q and len(search_q) >= 2:
        endpoint   = "/competitions/search"
        params["q"] = search_q
    else:
        endpoint = "/competitions"

    result = api_get(endpoint, params=params)
    if not result:
        st.stop()

    total = result["total"]
    pages = result["pages"]
    items = result["items"]

    # ── Result header + export ────────────────────────────────────
    rh1, rh2 = st.columns([5, 1])
    with rh1:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:12px;padding:6px 0;'>"
            f"<span style='font-size:1.1rem;font-weight:800;color:#f0f4f8;'>Competition Results</span>"
            f"<span class='result-chip'>{total:,} found</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
    with rh2:
        if items:
            DISPLAY_COLS = {
                "id": "ID", "branch": "Nama Lomba", "level": "Level",
                "sector": "Sektor", "type": "Tipe",
                "score": "Skor", "rating": "Rating", "batch_raw": "Batch",
            }
            _df       = pd.DataFrame(items)
            _show     = [c for c in DISPLAY_COLS if c in _df.columns]
            _csv_df   = _df[_show].rename(columns=DISPLAY_COLS)
            if "Skor" in _csv_df: _csv_df["Skor"] = _csv_df["Skor"].round(2)
            st.download_button(
                label="⬇️ Export CSV",
                data=_csv_df.to_csv(index=False).encode("utf-8"),
                file_name="simt_filtered.csv",
                mime="text/csv",
                width='stretch',
            )

    # ── Data table ────────────────────────────────────────────────
    if not items:
        st.markdown("""
        <div style='background:rgba(19,127,236,0.05);border:1px dashed rgba(19,127,236,0.2);
                    border-radius:12px;padding:2.5rem;text-align:center;color:#8a9bb0;'>
            <div style='font-size:2rem;margin-bottom:.5rem'>🔍</div>
            Tidak ada hasil untuk filter ini.
        </div>
        """, unsafe_allow_html=True)
    else:
        DISPLAY_COLS = {
            "id": "ID", "branch": "Nama Lomba", "level": "Level",
            "sector": "Sektor", "type": "Tipe",
            "score": "Skor", "rating": "Rating ⭐", "batch_raw": "Batch",
        }
        df       = pd.DataFrame(items)
        show     = [c for c in DISPLAY_COLS if c in df.columns]
        disp_df  = df[show].rename(columns=DISPLAY_COLS)
        if "Skor" in disp_df: disp_df["Skor"] = disp_df["Skor"].round(2)

        st.markdown("<div class='section-card' style='padding:0;overflow:hidden;'>", unsafe_allow_html=True)
        st.dataframe(
            disp_df,
            hide_index=True,
            width='stretch',
            height=480,
            column_config={
                "Rating ⭐": st.column_config.NumberColumn(format="%d ⭐"),
                "Skor":      st.column_config.NumberColumn(format="%.2f"),
            },
        )
        st.markdown("</div>", unsafe_allow_html=True)

        # ── Detail expander ──────────────────────────────────────
        st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
        selected_id = st.selectbox(
            "Lihat detail (pilih ID):",
            options=[None] + [str(i["id"]) for i in items],
            format_func=lambda x: "— pilih —" if x is None else f"ID {x}",
        )
        if selected_id:
            detail = api_get(f"/competitions/{selected_id}")
            if detail:
                with st.expander(f"📋 Detail: {detail['branch']}", expanded=True):
                    d1, d2, d3 = st.columns(3)
                    d1.write(f"**Level:** {detail.get('level', '-')}")
                    d1.write(f"**Tipe:** {detail.get('type', '-')}")
                    d1.write(f"**Sektor:** {detail.get('sector', '-')}")
                    d2.write(f"**Skor:** {detail.get('score', '-')}")
                    d2.write(f"**Rating:** {'⭐' * (detail.get('rating') or 0)}")
                    d2.write(f"**Cluster:** {detail.get('cluster', '-')}")
                    if detail.get("event"):
                        ev = detail["event"]
                        d3.write(f"**Event:** {ev.get('name', '-')}")
                        d3.write(f"**Tanggal:** {ev.get('competition_start', '-')} → {ev.get('competition_end', '-')}")
                        d3.write(f"**Negara:** {ev.get('country', '-')}")
                        if ev.get("useful_link"):
                            st.markdown(f"🔗 [Link Kompetisi]({ev['useful_link'].split(',')[0].strip()})")
                    if detail.get("organizer"):
                        org = detail["organizer"]
                        st.write(f"**Penyelenggara:** {org.get('name', '-')}")
                        if org.get("useful_link"):
                            st.markdown(f"🔗 [Website]({org['useful_link']})")

    # ── Pagination ────────────────────────────────────────────────
    st.markdown("<div style='height:.75rem'></div>", unsafe_allow_html=True)
    cp, ci, cn = st.columns([1, 3, 1])
    with cp:
        if st.button("← Sebelumnya", disabled=st.session_state.search_page <= 1,
                     width='stretch'):
            st.session_state.search_page -= 1
            st.rerun()
    with ci:
        st.markdown(
            f"<div style='text-align:center;color:#8a9bb0;font-size:.85rem;padding-top:.5rem;'>"
            f"Halaman <b style='color:#f0f4f8'>{st.session_state.search_page}</b> / {pages}</div>",
            unsafe_allow_html=True,
        )
    with cn:
        if st.button("Berikutnya →", disabled=st.session_state.search_page >= pages,
                     width='stretch'):
            st.session_state.search_page += 1
            st.rerun()


# ════════════════════════════════════════════════════════════════
# PAGE 5: SCORE DEEP-DIVE
# ════════════════════════════════════════════════════════════════
elif active == "score":
    st.markdown("""
    <div class='page-header'>
        <h1>Score Deep-Dive</h1>
        <p>Analisis mendalam distribusi skor, pola rating, dan tren per batch.</p>
    </div>
    """, unsafe_allow_html=True)

    score_data = api_get("/analytics/score-distribution")
    if not score_data:
        st.stop()

    score_df = pd.DataFrame(score_data)

    # ── Rating threshold table ────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-card-title'>🎯 Rating Threshold Reverse-Engineering</div>"
        "<div class='section-card-subtitle'>Rentang skor dan jumlah kompetisi tiap bintang rating</div>",
        unsafe_allow_html=True,
    )
    styled = score_df[["rating", "count", "min_score", "avg_score", "max_score"]].copy()
    styled.columns = ["Rating ⭐", "Jumlah", "Skor Min", "Avg Skor", "Skor Maks"]
    st.dataframe(styled, hide_index=True, width='stretch')
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────
    cl, cr = st.columns(2)
    RATING_COLORS = ["#ef4444", "#f59e0b", "#f97316", "#137fec", "#6366f1", "#10b981"]

    with cl:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-card-title'>Distribution per Rating</div>", unsafe_allow_html=True)
        fig = px.bar(
            score_df, x="rating", y="count",
            color="rating",
            color_continuous_scale=["#ef4444", "#f59e0b", "#137fec", "#6366f1", "#10b981", "#14b8a6"],
            text="count",
            labels={"rating": "Rating ⭐", "count": "Jumlah"},
        )
        fig.update_traces(textposition="outside", textfont_color="#f0f4f8", marker_line_width=0)
        apply_theme(fig, 340)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    with cr:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown("<div class='section-card-title'>Score Range per Rating</div>", unsafe_allow_html=True)
        fig = go.Figure()
        for _, row in score_df.iterrows():
            r     = int(row["rating"]) if row["rating"] >= 0 else 0
            color = RATING_COLORS[r % len(RATING_COLORS)]
            fig.add_trace(go.Bar(
                name=f"Rating {row['rating']}⭐",
                x=[f"Rating {row['rating']}"],
                y=[row["max_score"] - row["min_score"]],
                base=[row["min_score"]],
                marker_color=color,
                marker_line_width=0,
                text=[f"{row['min_score']:.1f}–{row['max_score']:.1f}"],
                textposition="inside",
                insidetextanchor="middle",
            ))
        apply_theme(fig, 340)
        fig.update_layout(
            barmode="stack", showlegend=False,
            yaxis_title="Skor", xaxis_title="Rating",
        )
        st.plotly_chart(fig, width='stretch')
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Batch trend ───────────────────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-card-title'>📦 Batch Trend</div>"
        "<div class='section-card-subtitle'>Standar kurasi dari waktu ke waktu per batch</div>",
        unsafe_allow_html=True,
    )
    batch_data = api_get("/analytics/by-batch")
    if batch_data:
        batch_df = pd.DataFrame(batch_data).dropna(subset=["batch_num"])
        batch_df["label"] = batch_df.apply(
            lambda r: f"B{int(r['batch_num'])}/{int(r['batch_year'])}"
                      if r["batch_year"] else f"B{int(r['batch_num'])}",
            axis=1,
        )
        fig = px.scatter(
            batch_df, x="label", y="avg_score",
            size="count", color="avg_score",
            color_continuous_scale=["#ef4444", "#f59e0b", "#10b981"],
            text="count",
            labels={"label": "Batch", "avg_score": "Avg Skor", "count": "Jumlah"},
        )
        fig.add_hline(
            y=batch_df["avg_score"].mean(), line_dash="dot",
            line_color="rgba(255,255,255,0.2)",
            annotation_text="Rata-rata",
            annotation_font_color="#8a9bb0", annotation_font_size=11,
        )
        apply_theme(fig, 380)
        fig.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Data batch tidak tersedia.")
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Intra-competition variance ────────────────────────────────
    st.markdown("<div class='section-card'>", unsafe_allow_html=True)
    st.markdown(
        "<div class='section-card-title'>🔀 Variasi Skor Antar-Cabang dalam Satu Event</div>"
        "<div class='section-card-subtitle'>Event dengan rentang skor tertinggi — ada cabang sangat baik dan sangat buruk dalam event yang sama.</div>",
        unsafe_allow_html=True,
    )
    variance_data = api_get("/analytics/intra-competition-variance", params={"limit": 15})
    if variance_data:
        var_df = pd.DataFrame(variance_data)
        var_df["event_name_short"] = var_df["event_name"].str[:65]
        fig = px.bar(
            var_df.sort_values("score_range", ascending=True),
            x="score_range", y="event_name_short", orientation="h",
            color="score_range",
            color_continuous_scale=["#137fec", "#f59e0b", "#ef4444"],
            text="branch_count",
            labels={"score_range": "Rentang Skor (Max-Min)", "event_name_short": ""},
        )
        fig.update_traces(
            texttemplate="%{text} cabang", textposition="outside",
            textfont_color="#f0f4f8", marker_line_width=0,
        )
        apply_theme(fig, 480)
        fig.update_layout(showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("Data variance tidak tersedia.")
    st.markdown("</div>", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════
# PAGE 6: AI ASSISTANT (CHATBOT)
# ════════════════════════════════════════════════════════════════
elif active == "chatbot":
    st.markdown("""
    <div class='page-header'>
        <h1>AI Assistant</h1>
        <p>Tanya apa saja tentang data kompetisi SIMT — didukung DeepSeek V3 via Chutes.</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Token check ───────────────────────────────────────────────
    if not CHUTES_TOKEN:
        st.error(
            "**CHUTES_API_TOKEN belum diset.**  \n"
            "Buat file `.env` di root project dan tambahkan:"
        )
        st.code("CHUTES_API_TOKEN=your_token_here", language="bash")
        st.stop()

    # ── Enrich system prompt with live context ─────────────────────
    overview = api_get("/analytics/overview") or {}
    dynamic_ctx = ""
    if overview:
        dynamic_ctx = (
            f"\n\nData ringkas dari database saat ini:\n"
            f"- Total kompetisi  : {overview.get('total_competitions', 'N/A')}\n"
            f"- Total event unik : {overview.get('total_events', 'N/A')}\n"
            f"- Total penyelenggara: {overview.get('total_organizers', 'N/A')}\n"
            f"- Total negara     : {overview.get('total_countries', 'N/A')}\n"
            f"- Rata-rata skor   : {overview.get('avg_score', 'N/A')}\n"
        )
    system_msg = {"role": "system", "content": SIMT_SYSTEM_PROMPT + dynamic_ctx}

    # ── Session state ─────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Suggested starters ────────────────────────────────────────
    SUGGESTIONS = [
        "Kompetisi apa saja yang levelnya Internasional?",
        "Penyelenggara mana yang punya skor terbaik?",
        "Apa arti rating bintang dalam sistem SIMT?",
        "Ceritakan tren kompetisi 3 tahun terakhir.",
    ]

    if not st.session_state.chat_history:
        st.markdown("<div class='section-card'>", unsafe_allow_html=True)
        st.markdown(
            "<div class='section-card-title'>💡 Mulai percakapan</div>"
            "<div class='section-card-subtitle'>Pilih pertanyaan cepat atau ketik sendiri di bawah.</div>",
            unsafe_allow_html=True,
        )
        btn_cols = st.columns(2)
        for idx, sug in enumerate(SUGGESTIONS):
            with btn_cols[idx % 2]:
                if st.button(sug, key=f"sug_{idx}", width='stretch'):
                    st.session_state.chat_history.append({"role": "user", "content": sug})
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    # ── Chat history display ───────────────────────────────────────
    history_html = "<div class='chat-wrap'>"
    for msg in st.session_state.chat_history:
        if msg["role"] == "user":
            history_html += (
                "<div class='chat-bubble user'>"
                "  <div class='chat-avatar avatar-user'>👤</div>"
                "  <div>"
                f"    <div class='chat-text chat-text-user'>{msg['content']}</div>"
                "    <div class='chat-meta'>Kamu</div>"
                "  </div>"
                "</div>"
            )
        elif msg["role"] == "assistant":
            history_html += (
                "<div class='chat-bubble'>"
                "  <div class='chat-avatar avatar-ai'>🤖</div>"
                "  <div>"
                f"    <div class='chat-text chat-text-ai'>{msg['content']}</div>"
                "    <div class='chat-meta'>AI Assistant</div>"
                "  </div>"
                "</div>"
            )
    history_html += "</div>"
    if st.session_state.chat_history:
        st.markdown(history_html, unsafe_allow_html=True)

    # ── Input + streaming ─────────────────────────────────────────
    user_input = st.chat_input("Tanya tentang data kompetisi...")
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        messages = [system_msg] + [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.chat_history
        ]

        placeholder = st.empty()
        full_response = ""
        try:
            for delta in stream_chutes(messages, token=CHUTES_TOKEN):
                full_response += delta
                placeholder.markdown(
                    f"<div class='chat-bubble'>"
                    f"  <div class='chat-avatar avatar-ai'>🤖</div>"
                    f"  <div>"
                    f"    <div class='chat-text chat-text-ai'>{full_response}▌</div>"
                    f"    <div class='chat-meta'>AI Assistant</div>"
                    f"  </div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            placeholder.markdown(
                f"<div class='chat-bubble'>"
                f"  <div class='chat-avatar avatar-ai'>🤖</div>"
                f"  <div>"
                f"    <div class='chat-text chat-text-ai'>{full_response}</div>"
                f"    <div class='chat-meta'>AI Assistant</div>"
                f"  </div>"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.session_state.chat_history.append(
                {"role": "assistant", "content": full_response}
            )
        except httpx.HTTPStatusError as exc:
            st.error(f"API error {exc.response.status_code}: {exc.response.text}")
        except httpx.RequestError as exc:
            st.error(f"Gagal menghubungi Chutes API: {exc}")

        st.rerun()

    # ── Bottom controls ───────────────────────────────────────────
    if st.session_state.chat_history:
        col_clear, col_export, _ = st.columns([1, 1.5, 5])
        with col_clear:
            if st.button("🗑️ Clear Chat", width='stretch'):
                st.session_state.chat_history = []
                st.rerun()
        with col_export:
            export_text = "\n\n".join(
                f"{'Kamu' if m['role'] == 'user' else 'AI'}: {m['content']}"
                for m in st.session_state.chat_history
            )
            st.download_button(
                "⬇️ Export Chat",
                data=export_text,
                file_name="simt_chat_export.txt",
                mime="text/plain",
                width='stretch',
            )
