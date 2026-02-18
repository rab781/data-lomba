"""
SIMT Kompetisi Explorer — Streamlit Dashboard
═══════════════════════════════════════════════

5 Pages:
  1. 📊 Overview          — KPI cards + distribution charts
  2. 🏆 Organizer Quality — Scatter plot + "pabrik lomba" analysis
  3. 🗺  Geography         — Country breakdown + map
  4. 🔍 Search & Filter   — Interactive search + export
  5. 📈 Score Deep-Dive   — Distribution, thresholds, batch trend

Run:
    streamlit run dashboard/app.py
"""
import sys
import math
from pathlib import Path
from typing import Any

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── Config ────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000/api"

st.set_page_config(
    page_title = "SIMT Kompetisi Explorer",
    page_icon  = "🏅",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(118, 75, 162, 0.3);
    }
    .metric-card .value { font-size: 2rem; font-weight: 800; }
    .metric-card .label { font-size: 0.85rem; opacity: 0.9; margin-top: 0.2rem; }
    .flag-badge {
        background: #ff4b4b; color: white;
        padding: 2px 8px; border-radius: 12px;
        font-size: 0.75rem; font-weight: bold;
    }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; }
</style>
""", unsafe_allow_html=True)


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


# ── Sidebar navigation ────────────────────────────────────────────
PAGES = {
    "📊 Overview":           "overview",
    "🏆 Organizer Quality":  "organizer",
    "🗺️  Geography":         "geography",
    "🔍 Search & Filter":    "search",
    "📈 Score Deep-Dive":    "score",
}

with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/Flag_of_Indonesia.svg/160px-Flag_of_Indonesia.svg.png", width=60)
    st.title("SIMT Explorer")
    st.caption("Data Kurasi Lomba Kemendikdasmen")
    st.divider()

    page = st.radio("Navigasi", list(PAGES.keys()), label_visibility="collapsed")
    active = PAGES[page]

    st.divider()
    if check_api():
        st.success("API Connected ✓", icon="🟢")
    else:
        st.error("API Offline — jalankan:\n`uvicorn api.main:app --reload`", icon="🔴")
        st.stop()


# ════════════════════════════════════════════════════════════════
# PAGE 1: OVERVIEW
# ════════════════════════════════════════════════════════════════
if active == "overview":
    st.title("📊 Overview — Ekosistem Kompetisi SIMT")
    st.caption("Gambaran menyeluruh 4.981+ kompetisi yang dikurasi oleh Kemendikdasmen.")

    data = api_get("/analytics/overview")
    if not data:
        st.stop()

    # ── KPI Cards ────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    kpis = [
        (c1, data["total_competitions"], "Total Lomba"),
        (c2, data["total_events"],       "Event Unik"),
        (c3, data["total_organizers"],   "Penyelenggara"),
        (c4, data["total_countries"],    "Negara"),
        (c5, f"{data['avg_score']:.1f}", "Rata-rata Skor"),
    ]
    for col, val, label in kpis:
        display = f"{val:,}" if isinstance(val, int) else str(val)
        col.markdown(f"""
        <div class="metric-card">
            <div class="value">{display}</div>
            <div class="label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # ── Row 1: Cluster pie + Level bar ──────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Distribusi per Cluster")
        cluster_df = pd.DataFrame(data["cluster_distribution"])
        fig = px.pie(
            cluster_df, values="count", names="label",
            color_discrete_sequence=px.colors.qualitative.Set2,
            hole=0.4,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Level Kompetisi")
        level_df = pd.DataFrame(data["level_distribution"])
        fig = px.bar(
            level_df, x="count", y="label", orientation="h",
            color="avg_score", color_continuous_scale="Viridis",
            text="count", labels={"label": "", "count": "Jumlah", "avg_score": "Avg Score"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(margin=dict(t=20, b=20), coloraxis_showscale=True)
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 2: Sector bar ────────────────────────────────────────
    st.subheader("Top Sektor Kompetisi")
    sector_data = api_get("/analytics/by-sector")
    if sector_data:
        sector_df = pd.DataFrame(sector_data).sort_values("count", ascending=True)
        fig = px.bar(
            sector_df, x="count", y="sector", orientation="h",
            color="avg_score", color_continuous_scale="RdYlGn",
            text="count", labels={"sector": "", "count": "Jumlah", "avg_score": "Avg Score"},
            title="Jumlah Lomba per Sektor (warna = rata-rata skor)",
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=450, margin=dict(t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 3: Tren per tahun ────────────────────────────────────
    st.subheader("Tren Jumlah Kompetisi per Tahun")
    year_data = api_get("/analytics/by-year")
    if year_data:
        year_df = pd.DataFrame(year_data).dropna(subset=["year"])
        year_df["year"] = year_df["year"].astype(str)
        fig = px.line(
            year_df, x="year", y="count", markers=True,
            labels={"year": "Tahun", "count": "Jumlah Lomba"},
        )
        fig.add_bar(x=year_df["year"], y=year_df["count"], opacity=0.3, name="Jumlah")
        fig.update_layout(showlegend=False, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ── Row 4: Level × Cluster heatmap ───────────────────────────
    with st.expander("🔍 Level × Cluster Matrix"):
        comp_data = api_get("/competitions", params={"per_page": 100, "page": 1})
        if comp_data:
            # Pull full data for pivot (use analytics by-level as proxy)
            level_data = api_get("/analytics/by-level")
            st.json(level_data)


# ════════════════════════════════════════════════════════════════
# PAGE 2: ORGANIZER QUALITY
# ════════════════════════════════════════════════════════════════
elif active == "organizer":
    st.title("🏆 Analisis Kualitas Penyelenggara")
    st.caption("Petakan reputasi penyelenggara — dari organizer terpercaya hingga 'pabrik lomba'.")

    org_data = api_get("/analytics/organizer-quality")
    if not org_data:
        st.stop()

    df = pd.DataFrame(org_data)

    # ── KPI row ──────────────────────────────────────────────────
    total_org  = len(df)
    pabrik     = df[df["is_flagged"] == True]
    avg_q      = df["avg_score"].mean()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Penyelenggara", f"{total_org:,}")
    c2.metric("Flagged 'Pabrik Lomba'", f"{len(pabrik):,}", help="Count ≥20 & Avg Score <45")
    c3.metric("Avg Skor Keseluruhan", f"{avg_q:.1f}" if avg_q else "N/A")
    c4.metric("Penyelenggara Volume Tinggi (≥10)", f"{len(df[df['count'] >= 10]):,}")

    st.divider()

    # ── Main scatter plot ─────────────────────────────────────────
    st.subheader("Scatter: Volume vs Kualitas Penyelenggara")
    st.caption("Titik di kiri-bawah = banyak lomba tapi skor rendah (**pabrik lomba**). Titik di kanan-atas = organizer berkualitas.")

    df["color"] = df["is_flagged"].map({True: "🚩 Pabrik Lomba", False: "✅ Normal"})
    df["display_name"] = df["name"].str[:40]

    fig = px.scatter(
        df, x="count", y="avg_score",
        color="color",
        color_discrete_map={"🚩 Pabrik Lomba": "#ff4b4b", "✅ Normal": "#2196F3"},
        hover_name="name",
        hover_data={"count": True, "avg_score": ":.2f", "avg_rating": ":.1f", "color": False},
        size="count", size_max=40,
        labels={"count": "Jumlah Lomba", "avg_score": "Rata-rata Skor", "color": "Kategori"},
        title="Semua Penyelenggara: Volume vs Kualitas",
    )
    # Add quadrant annotations
    fig.add_hline(y=45, line_dash="dash", line_color="gray", annotation_text="Threshold Skor 45")
    fig.add_vline(x=20, line_dash="dash", line_color="gray", annotation_text="Threshold Volume 20")
    fig.update_layout(height=500, margin=dict(t=60))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Top vs Bottom organizers ──────────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("🥇 Top 15 Penyelenggara (Avg Score)")
        top15 = df.nlargest(15, "avg_score")[["name", "count", "avg_score", "avg_rating"]]
        top15.columns = ["Penyelenggara", "Jml Lomba", "Avg Score", "Avg Rating"]
        top15["Avg Score"] = top15["Avg Score"].round(2)
        st.dataframe(top15, hide_index=True, use_container_width=True)

    with col_r:
        st.subheader("🚨 Flagged 'Pabrik Lomba'")
        if len(pabrik):
            pabrik_show = pabrik[["name", "count", "avg_score", "avg_rating"]].sort_values("count", ascending=False)
            pabrik_show.columns = ["Penyelenggara", "Jml Lomba", "Avg Score", "Avg Rating"]
            pabrik_show["Avg Score"] = pabrik_show["Avg Score"].round(2)
            st.dataframe(pabrik_show, hide_index=True, use_container_width=True)
        else:
            st.info("Tidak ada penyelenggara yang di-flag dengan kriteria saat ini.")

    st.divider()

    # ── Level comparison box ──────────────────────────────────────
    st.subheader("Distribusi Skor: Internasional vs Nasional vs Provinsi")
    level_scores = api_get("/analytics/by-level")
    if level_scores:
        s_df = pd.DataFrame(level_scores)
        fig = px.bar(
            s_df, x="level", y="avg_score",
            error_y=s_df["max_score"] - s_df["avg_score"],
            error_y_minus=s_df["avg_score"] - s_df["min_score"],
            color="level",
            labels={"level": "Level", "avg_score": "Rata-rata Skor"},
            text="avg_score",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════════════
# PAGE 3: GEOGRAPHY
# ════════════════════════════════════════════════════════════════
elif active == "geography":
    st.title("🗺️ Sebaran Geografis Kompetisi")
    st.caption("Distribusi kompetisi berdasarkan negara penyelenggara.")

    country_data = api_get("/analytics/by-country")
    if not country_data:
        st.stop()

    df = pd.DataFrame(country_data)

    # ── KPI ──────────────────────────────────────────────────────
    total_countries = len(df)
    id_count        = df[df["country_code"] == "ID"]["count"].sum() if "ID" in df["country_code"].values else 0
    intl_pct        = (1 - id_count / df["count"].sum()) * 100

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Negara", total_countries)
    c2.metric("Lomba di Indonesia", f"{int(id_count):,}")
    c3.metric("Lomba di Luar Negeri", f"{intl_pct:.1f}%")

    st.divider()

    # ── Choropleth map ────────────────────────────────────────────
    st.subheader("Peta Sebaran Kompetisi")
    fig = px.choropleth(
        df,
        locations      = "country_code",
        color          = "count",
        hover_name     = "country",
        hover_data     = {"count": True, "avg_score": ":.2f", "country_code": False},
        color_continuous_scale = "Blues",
        labels         = {"count": "Jumlah Lomba"},
    )
    fig.update_layout(
        geo = dict(showframe=False, showcoastlines=True, projection_type="natural earth"),
        margin = dict(t=0, b=0, l=0, r=0),
        height = 450,
        coloraxis_colorbar = dict(title="Jumlah Lomba"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Bar chart top countries ──────────────────────────────────
    st.subheader("Top 20 Negara Penyelenggara")
    top_df = df.nlargest(20, "count").sort_values("count")
    fig = px.bar(
        top_df, x="count", y="country", orientation="h",
        color="avg_score", color_continuous_scale="YlOrRd",
        text="count",
        labels={"count": "Jumlah Lomba", "country": "", "avg_score": "Avg Score"},
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=500, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── Insight: "Internasional" yang tetap di Indonesia ─────────
    with st.expander("💡 Insight: Berapa % 'Internasional' yang digelar di Indonesia?"):
        st.markdown("""
        Banyak lomba berlabel **Internasional** tetapi diselenggarakan di Indonesia.
        Ini wajar — label 'Internasional' bisa berarti:
        - Peserta dari berbagai negara, tapi venue di Jakarta/Bali
        - Afiliasi dengan badan internasional (FIDE, IEA, dll.)
        
        Analisis ini membantu membedakan kompetisi yang **benar-benar diselenggarakan di luar negeri** 
        vs. yang hanya internasional secara nama/peserta.
        """)
        comp_intl_id = api_get("/competitions", params={
            "level": "Internasional", "per_page": 1, "country_code": "ID"
        })
        comp_intl_all = api_get("/competitions", params={
            "level": "Internasional", "per_page": 1
        })
        if comp_intl_id and comp_intl_all:
            pct = comp_intl_id["total"] / comp_intl_all["total"] * 100
            st.metric(
                "Lomba Internasional yang digelar di Indonesia",
                f"{comp_intl_id['total']:,} / {comp_intl_all['total']:,}",
                f"{pct:.1f}% dari total Internasional",
            )


# ════════════════════════════════════════════════════════════════
# PAGE 4: SEARCH & FILTER
# ════════════════════════════════════════════════════════════════
elif active == "search":
    st.title("🔍 Pencarian & Filter Kompetisi")
    st.caption("Temukan lomba sesuai minat, level, dan bidangmu.")

    # Load filter options
    options = api_get("/competitions/filters/options") or {}

    # ── Filter sidebar ────────────────────────────────────────────
    with st.sidebar:
        st.subheader("🎛️ Filter")
        search_q    = st.text_input("🔍 Cari nama lomba / penyelenggara", placeholder="e.g. Olimpiade, BRIN, Chess...")
        f_level     = st.selectbox("Level",   ["Semua"] + options.get("levels",   []))
        f_sector    = st.selectbox("Sektor",  ["Semua"] + options.get("sectors",  []))
        f_cluster   = st.selectbox("Cluster", ["Semua"] + options.get("clusters", []))
        f_type      = st.selectbox("Tipe",    ["Semua"] + options.get("types",    []))
        f_rating    = st.slider("Min Rating ⭐", 0, 5, 0)
        year_range  = options.get("years", [])
        if year_range:
            f_year  = st.select_slider(
                "Tahun Pelaksanaan",
                options     = year_range,
                value       = (year_range[0], year_range[-1]),
            )
        else:
            f_year  = None

        country_opts = [f"{c['name']} ({c['code']})" for c in options.get("countries", [])]
        f_country_sel = st.selectbox("Negara", ["Semua"] + country_opts)
        f_country_code = None
        if f_country_sel != "Semua":
            f_country_code = f_country_sel.split("(")[-1].rstrip(")")

        sort_by = st.selectbox("Urutkan",  ["score", "rating", "id"])
        order   = st.radio("Urutan", ["desc", "asc"], horizontal=True)

    # ── Build params ──────────────────────────────────────────────
    per_page = 25

    if "search_page" not in st.session_state:
        st.session_state.search_page = 1

    params: dict = {
        "per_page": per_page,
        "page":     st.session_state.search_page,
        "sort_by":  sort_by,
        "order":    order,
    }
    if f_level    != "Semua": params["level"]    = f_level
    if f_sector   != "Semua": params["sector"]   = f_sector
    if f_cluster  != "Semua": params["cluster"]  = f_cluster
    if f_type     != "Semua": params["type"]     = f_type
    if f_rating   > 0:        params["rating_min"] = f_rating
    if f_country_code:        params["country_code"] = f_country_code
    if f_year and year_range:
        params["year_start"] = f_year[0]
        params["year_end"]   = f_year[1]

    # Use search endpoint if query is provided
    if search_q and len(search_q) >= 2:
        endpoint = "/competitions/search"
        params["q"] = search_q
    else:
        endpoint = "/competitions"

    result = api_get(endpoint, params=params)
    if not result:
        st.stop()

    total    = result["total"]
    pages    = result["pages"]
    items    = result["items"]

    # ── Results header ────────────────────────────────────────────
    st.markdown(f"**{total:,} kompetisi ditemukan** — Halaman {st.session_state.search_page}/{pages}")

    if not items:
        st.info("Tidak ada hasil untuk filter ini.")
    else:
        # ── Results table ─────────────────────────────────────────
        df = pd.DataFrame(items)

        DISPLAY_COLS = {
            "id":         "ID",
            "branch":     "Cabang/Nama Lomba",
            "level":      "Level",
            "sector":     "Sektor",
            "type":       "Tipe",
            "score":      "Skor",
            "rating":     "Rating ⭐",
            "batch_raw":  "Batch",
        }
        show_cols = [c for c in DISPLAY_COLS if c in df.columns]
        display_df = df[show_cols].rename(columns=DISPLAY_COLS)
        if "Skor" in display_df:
            display_df["Skor"] = display_df["Skor"].round(2)

        st.dataframe(
            display_df,
            hide_index     = True,
            use_container_width = True,
            height         = 480,
        )

        # ── Detail card on click ──────────────────────────────────
        selected_id = st.selectbox(
            "Lihat detail salah satu (pilih ID):",
            options   = [None] + [str(i["id"]) for i in items],
            format_func = lambda x: "— pilih —" if x is None else f"ID {x}",
        )
        if selected_id:
            detail = api_get(f"/competitions/{selected_id}")
            if detail:
                with st.expander(f"📋 Detail: {detail['branch']}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Level:** {detail.get('level', '-')}")
                    c1.write(f"**Tipe:** {detail.get('type', '-')}")
                    c1.write(f"**Sektor:** {detail.get('sector', '-')}")
                    c2.write(f"**Skor:** {detail.get('score', '-')}")
                    c2.write(f"**Rating:** {'⭐' * (detail.get('rating') or 0)}")
                    c2.write(f"**Cluster:** {detail.get('cluster', '-')}")
                    if detail.get("event"):
                        ev = detail["event"]
                        c3.write(f"**Kompetisi:** {ev.get('name', '-')}")
                        c3.write(f"**Tanggal:** {ev.get('competition_start', '-')} → {ev.get('competition_end', '-')}")
                        c3.write(f"**Negara:** {ev.get('country', '-')}")
                        if ev.get("useful_link"):
                            st.markdown(f"🔗 [Link Kompetisi]({ev['useful_link'].split(',')[0].strip()})")
                    if detail.get("organizer"):
                        org = detail["organizer"]
                        st.write(f"**Penyelenggara:** {org.get('name', '-')}")
                        if org.get("useful_link"):
                            st.markdown(f"🔗 [Website Penyelenggara]({org['useful_link']})")

        # ── Export ────────────────────────────────────────────────
        st.divider()
        csv_data = display_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label    = "⬇️ Download hasil sebagai CSV",
            data     = csv_data,
            file_name = "simt_filtered_results.csv",
            mime     = "text/csv",
        )

        # ── Pagination ────────────────────────────────────────────
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("← Sebelumnya", disabled=st.session_state.search_page <= 1):
                st.session_state.search_page -= 1
                st.rerun()
        with col_info:
            st.markdown(f"<center>Hal. **{st.session_state.search_page}** / {pages}</center>", unsafe_allow_html=True)
        with col_next:
            if st.button("Berikutnya →", disabled=st.session_state.search_page >= pages):
                st.session_state.search_page += 1
                st.rerun()


# ════════════════════════════════════════════════════════════════
# PAGE 5: SCORE DEEP-DIVE
# ════════════════════════════════════════════════════════════════
elif active == "score":
    st.title("📈 Score Deep-Dive")
    st.caption("Analisis mendalam distribusi skor, pola rating, dan tren per batch.")

    score_data = api_get("/analytics/score-distribution")
    if not score_data:
        st.stop()

    score_df = pd.DataFrame(score_data)

    # ── Row 1: Rating threshold table ────────────────────────────
    st.subheader("🎯 Reverse-Engineering Rating Thresholds")
    st.caption("Rating ditentukan algoritmis dari skor. Tabel ini menunjukkan rentang skor tiap rating.")

    styled = score_df[["rating", "count", "min_score", "avg_score", "max_score"]].copy()
    styled.columns = ["Rating ⭐", "Jumlah", "Skor Min", "Avg Skor", "Skor Maks"]
    st.dataframe(styled, hide_index=True, use_container_width=True)

    st.divider()

    # ── Row 2: Bar chart score dist ──────────────────────────────
    col_l, col_r = st.columns(2)

    with col_l:
        st.subheader("Distribusi Jumlah per Rating")
        fig = px.bar(
            score_df, x="rating", y="count",
            color="rating",
            color_continuous_scale="RdYlGn",
            text="count",
            labels={"rating": "Rating ⭐", "count": "Jumlah"},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=380, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Rentang Skor per Rating")
        fig = go.Figure()
        colors = ["#d32f2f", "#e64a19", "#f57c00", "#fbc02d", "#388e3c", "#1565c0"]
        for _, row in score_df.iterrows():
            r = int(row["rating"]) if row["rating"] >= 0 else 0
            color = colors[r] if r < len(colors) else "#888"
            fig.add_trace(go.Bar(
                name    = f"Rating {row['rating']}⭐",
                x       = [f"Rating {row['rating']}"],
                y       = [row["max_score"] - row["min_score"]],
                base    = [row["min_score"]],
                marker_color = color,
                text    = [f"{row['min_score']:.1f}–{row['max_score']:.1f}"],
                textposition = "inside",
            ))
        fig.update_layout(
            barmode="stack", height=380, showlegend=False,
            yaxis_title="Skor", xaxis_title="Rating",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Row 3: Batch trend ────────────────────────────────────────
    st.subheader("📦 Tren Skor per Batch (Standar Kurasi dari Waktu ke Waktu)")
    batch_data = api_get("/analytics/by-batch")
    if batch_data:
        batch_df = pd.DataFrame(batch_data).dropna(subset=["batch_num"])
        batch_df["label"] = batch_df.apply(
            lambda r: f"B{int(r['batch_num'])}/{int(r['batch_year'])}" if r["batch_year"] else f"B{int(r['batch_num'])}",
            axis=1
        )
        fig = px.scatter(
            batch_df, x="label", y="avg_score",
            size="count", color="avg_score",
            color_continuous_scale="RdYlGn",
            text="count",
            labels={"label": "Batch", "avg_score": "Avg Skor", "count": "Jumlah"},
            title="Rata-rata Skor per Batch Kurasi",
        )
        fig.add_hline(y=batch_df["avg_score"].mean(), line_dash="dash",
                      annotation_text="Rata-rata keseluruhan")
        fig.update_layout(height=400, margin=dict(t=50))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Row 4: Intra-competition variance ─────────────────────────
    st.subheader("🔀 Variasi Skor Antar-Cabang dalam Satu Event")
    st.caption("Event dengan rentang skor tertinggi — artinya ada cabang yang sangat bagus dan ada yang sangat buruk dalam event yang sama.")
    variance_data = api_get("/analytics/intra-competition-variance", params={"limit": 15})
    if variance_data:
        var_df = pd.DataFrame(variance_data)
        var_df["event_name_short"] = var_df["event_name"].str[:60]
        fig = px.bar(
            var_df.sort_values("score_range", ascending=True),
            x="score_range", y="event_name_short",
            orientation="h",
            color="score_range",
            color_continuous_scale="Reds",
            text="branch_count",
            labels={"score_range": "Rentang Skor (Max-Min)", "event_name_short": ""},
        )
        fig.update_traces(texttemplate="%{text} cabang", textposition="outside")
        fig.update_layout(height=500, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
