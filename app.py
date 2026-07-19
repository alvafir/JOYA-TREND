
import os
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="JOYA TREND",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

CATEGORY_MAP = {
    "Goles": [
        "Sin gol 0-5",
        "Sin gol 0-10",
        "Sin gol 0-15",
        "Gol antes del 30",
        "Gol antes del 45",
        "Gol antes del 60",
        "Gol antes del 70",
        "+0.5 goles",
        "+1.5 goles",
        "+2.5 goles",
        "Ambos marcan",
        "Gol 1T",
        "Gol 2T",
        "0-0 al descanso",
        "Equipo +0.5 gol",
        "Equipo marca primero",
    ],
    "Tarjetas": [
        "+1.5 tarjetas",
        "+2.5 tarjetas",
        "+3.5 tarjetas",
        "Tarjeta 1T",
        "Equipo más tarjetas",
        "Árbitro over tarjetas",
    ],
    "Córners": [
        "+7.5 córners",
        "+8.5 córners",
        "+9.5 córners",
        "Córner 1T",
        "Equipo +3.5 córners",
        "Equipo +4.5 córners",
        "Equipo más córners",
    ],
    "Remates": [
        "+ tiros totales",
        "+ tiros al arco",
        "Equipo + tiros",
        "Jugador 1+ tiro",
        "Jugador 1+ tiro al arco",
    ],
    "Offsides": [
        "+1.5 offsides",
        "+2.5 offsides",
        "Equipo + offsides",
        "Equipo más offsides",
    ],
    "Resultado": [
        "Doble oportunidad",
        "DNB",
        "Gana cualquier mitad",
        "Handicap asiático",
        "Favorito +0.5 gol",
    ],
}

TIERS = ["S++", "S+", "A++", "NO BET"]


def load_data() -> pd.DataFrame:
    candidates = [
        DATA_DIR / "radar_tendencias.csv",
        Path("radar_tendencias.csv"),
    ]
    for path in candidates:
        if path.exists():
            df = pd.read_csv(path)
            return normalize(df)
    return demo_data()


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    expected = {
        "date": "",
        "league": "",
        "home_team": "",
        "away_team": "",
        "category": "Goles",
        "market": "",
        "home_hits": 0,
        "home_sample": 10,
        "away_hits": 0,
        "away_sample": 10,
        "league_rate": 0.0,
        "joya_score": 0.0,
        "tier": "NO BET",
        "calibrated_probability": np.nan,
        "odds": np.nan,
        "ev_pct": np.nan,
        "reliability_score": np.nan,
        "trend_strength": "Normal",
    }
    out = df.copy()
    for col, default in expected.items():
        if col not in out.columns:
            out[col] = default
    return out


def demo_data() -> pd.DataFrame:
    today = str(date.today())
    rows = [
        [today, "Premier League", "Equipo A", "Equipo B", "Goles", "Sin gol 0-10", 9, 10, 8, 10, 82, 93, "S++", 0.82, 1.42, 16.4, 88, "Muy fuerte"],
        [today, "La Liga", "Equipo C", "Equipo D", "Goles", "Gol antes del 70", 9, 10, 9, 10, 86, 92, "S++", 0.81, 1.36, 10.2, 86, "Muy fuerte"],
        [today, "Serie A", "Equipo E", "Equipo F", "Córners", "+8.5 córners", 8, 10, 9, 10, 79, 89, "S+", 0.76, 1.70, 29.2, 82, "Fuerte"],
        [today, "Liga Demo", "Equipo G", "Equipo H", "Tarjetas", "+2.5 tarjetas", 10, 10, 8, 10, 84, 91, "S++", 0.80, 1.50, 20.0, 84, "Muy fuerte"],
        [today, "Liga Demo", "Equipo I", "Equipo J", "Resultado", "Doble oportunidad", 9, 10, 8, 10, 78, 87, "S+", 0.75, 1.32, -1.0, 79, "Fuerte"],
        [today, "Liga Demo", "Equipo K", "Equipo L", "Offsides", "+1.5 offsides", 8, 10, 8, 10, 75, 85, "S+", 0.74, 1.62, 19.9, 77, "Fuerte"],
        [today, "Liga Demo", "Equipo M", "Equipo N", "Remates", "Equipo + tiros", 9, 10, 7, 10, 73, 83, "A++", 0.70, 1.75, 22.5, 71, "Aceptable"],
    ]
    cols = [
        "date","league","home_team","away_team","category","market",
        "home_hits","home_sample","away_hits","away_sample","league_rate",
        "joya_score","tier","calibrated_probability","odds","ev_pct",
        "reliability_score","trend_strength"
    ]
    return pd.DataFrame(rows, columns=cols)


def tier_rank(tier: str) -> int:
    return {"S++": 4, "S+": 3, "A++": 2, "NO BET": 1}.get(str(tier), 0)


def top_nucleo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    work = df.copy()
    work["tier_rank"] = work["tier"].map(tier_rank)
    work = work[work["tier"].isin(["S++", "S+", "A++"])]
    if work.empty:
        return work
    return (
        work.sort_values(
            ["home_team", "away_team", "tier_rank", "joya_score", "reliability_score"],
            ascending=[True, True, False, False, False],
        )
        .groupby(["home_team", "away_team"], as_index=False)
        .head(1)
        .sort_values(["tier_rank", "joya_score"], ascending=[False, False])
    )


def metric_pct(value):
    if pd.isna(value):
        return "N/D"
    return f"{float(value)*100:.1f}%" if float(value) <= 1 else f"{float(value):.1f}%"


st.title("💎 JOYA TREND")
st.caption("Radar de tendencias · Núcleo Sangrado · S++ · Value · Historial")

df = load_data()

with st.sidebar:
    st.header("Filtros")
    selected_date = st.date_input("Fecha", value=date.today())

    leagues = ["Todas"] + sorted(df["league"].dropna().astype(str).unique().tolist())
    selected_league = st.selectbox("Liga", leagues)

    categories = ["Todas"] + list(CATEGORY_MAP.keys())
    selected_category = st.selectbox("Categoría", categories)

    selected_tiers = st.multiselect(
        "Tier",
        ["S++", "S+", "A++", "NO BET"],
        default=["S++", "S+", "A++"],
    )

    min_score = st.slider("JOYA Score mínimo", 0, 100, 78)
    min_reliability = st.slider("Reliability mínimo", 0, 100, 60)

    st.divider()
    st.caption("JOYA TREND 8.0 Dashboard")

filtered = df.copy()

if "date" in filtered.columns:
    filtered["date"] = pd.to_datetime(filtered["date"], errors="coerce").dt.date
    filtered = filtered[filtered["date"] == selected_date]

if selected_league != "Todas":
    filtered = filtered[filtered["league"] == selected_league]

if selected_category != "Todas":
    filtered = filtered[filtered["category"] == selected_category]

filtered = filtered[
    filtered["tier"].isin(selected_tiers)
    & (pd.to_numeric(filtered["joya_score"], errors="coerce").fillna(0) >= min_score)
    & (pd.to_numeric(filtered["reliability_score"], errors="coerce").fillna(0) >= min_reliability)
]

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🏠 Inicio",
        "🩸 Núcleo Sangrado",
        "📡 Radar de Tendencias",
        "💰 Value",
        "📈 Historial",
    ]
)

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Partidos analizados", filtered[["home_team","away_team"]].drop_duplicates().shape[0])
    c2.metric("Tendencias S++", int((filtered["tier"] == "S++").sum()))
    c3.metric("Score máximo", f"{filtered['joya_score'].max():.1f}" if not filtered.empty else "N/D")
    c4.metric(
        "Reliability máximo",
        f"{filtered['reliability_score'].max():.1f}" if not filtered.empty else "N/D",
    )

    st.subheader("🔥 Top tendencias del día")
    top = filtered.sort_values(
        ["joya_score", "reliability_score"],
        ascending=[False, False],
    ).head(10)

    if top.empty:
        st.info("No hay tendencias que cumplan los filtros seleccionados.")
    else:
        for _, r in top.iterrows():
            with st.container(border=True):
                st.markdown(f"### ⚽ {r['home_team']} vs {r['away_team']}")
                st.markdown(f"**{r['market']}** · {r['category']}")
                a, b, c = st.columns(3)
                a.metric("JOYA Score", f"{r['joya_score']:.1f}/100")
                b.metric("Tier", str(r["tier"]))
                c.metric("Prob. calibrada", metric_pct(r["calibrated_probability"]))
                st.caption(
                    f"Local {int(r['home_hits'])}/{int(r['home_sample'])} · "
                    f"Visitante {int(r['away_hits'])}/{int(r['away_sample'])} · "
                    f"Liga {float(r['league_rate']):.1f}%"
                )

with tab2:
    st.subheader("🩸 Núcleo Sangrado")
    nucleo = top_nucleo(filtered)

    if nucleo.empty:
        st.warning("No hay selecciones A++ o superiores con los filtros actuales.")
    else:
        for _, r in nucleo.iterrows():
            with st.container(border=True):
                st.markdown(f"### {r['home_team']} vs {r['away_team']}")
                st.success(f"{r['market']} · {r['tier']}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Score", f"{r['joya_score']:.1f}")
                c2.metric("Fiabilidad", f"{r['reliability_score']:.1f}")
                c3.metric("Cuota", "N/D" if pd.isna(r["odds"]) else f"{r['odds']:.2f}")
                c4.metric("EV", "N/D" if pd.isna(r["ev_pct"]) else f"{r['ev_pct']:.1f}%")

with tab3:
    st.subheader("📡 Radar de Tendencias")
    st.caption("Ordena patrones repetitivos por fuerza, estabilidad y evidencia histórica.")

    radar_category = st.selectbox(
        "Explorar categoría",
        list(CATEGORY_MAP.keys()),
        key="radar_category",
    )

    radar = filtered[filtered["category"] == radar_category].copy()
    radar = radar.sort_values(
        ["joya_score", "reliability_score"],
        ascending=[False, False],
    )

    if radar.empty:
        st.info("No hay datos para esta categoría con los filtros actuales.")
    else:
        st.dataframe(
            radar[
                [
                    "league",
                    "home_team",
                    "away_team",
                    "market",
                    "joya_score",
                    "tier",
                    "reliability_score",
                    "league_rate",
                    "odds",
                    "ev_pct",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with tab4:
    st.subheader("💰 Radar de Value")
    value = filtered.copy()
    value["ev_pct"] = pd.to_numeric(value["ev_pct"], errors="coerce")
    value = value[value["ev_pct"].notna()].sort_values("ev_pct", ascending=False)

    if value.empty:
        st.info("No hay cuotas o EV disponible para los filtros actuales.")
    else:
        st.dataframe(
            value[
                [
                    "home_team",
                    "away_team",
                    "market",
                    "tier",
                    "calibrated_probability",
                    "odds",
                    "ev_pct",
                    "joya_score",
                    "reliability_score",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

with tab5:
    st.subheader("📈 Historial y rendimiento")
    st.info(
        "Esta sección queda preparada para conectarse a la base SQLite de JOYA TREND 7.0 "
        "y mostrar ROI, hit rate, CLV, rendimiento por liga, mercado y tier."
    )

    if not filtered.empty:
        summary = (
            filtered.groupby(["category", "tier"], dropna=False)
            .agg(
                tendencias=("market", "size"),
                score_promedio=("joya_score", "mean"),
                reliability_promedio=("reliability_score", "mean"),
            )
            .reset_index()
        )
        st.dataframe(summary, use_container_width=True, hide_index=True)

st.divider()
st.caption(
    "JOYA TREND es un sistema de apoyo estadístico. Los tiers y probabilidades "
    "son estimaciones y no garantizan resultados."
)
