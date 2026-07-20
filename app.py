from __future__ import annotations

import pandas as pd
import streamlit as st

from api.football_api import api_list, get_api_key, test_connection
from config.settings import DEFAULT_TIMEZONE
from database.database import initialize_database
from history.joya_brain import save_analysis_rows
from modules.explanation_engine import explain_market
from modules.league_analyzer import build_league_ranking
from modules.market_matrix import get_group_table
from modules.ranking_engine import (
    build_all_market_ranking,
    top_markets_by_league,
    top_markets_by_match,
)
from modules.scanner import scan_fixtures
from ui.sidebar import render_sidebar
from utils.filters import prepare_fixtures

st.set_page_config(page_title="JOYA X Enterprise", page_icon="💎", layout="wide")
initialize_database()

st.title("💎 JOYA X ENTERPRISE")
st.caption("Sprint 2 · Top 5 por partido · Explicaciones · Ranking global real · Top por liga")

if not get_api_key():
    st.error("Falta APISPORTS_KEY en Streamlit Secrets.")
    st.stop()

connected, connection_message = test_connection()
if connected:
    st.success(f"🟢 Conectado con API-Football · {connection_message}")
else:
    st.error(f"🔴 Sin conexión con API-Football · {connection_message}")
    st.stop()

settings = render_sidebar()
fixtures = api_list(
    "fixtures",
    {"date": settings["date"].isoformat(), "timezone": DEFAULT_TIMEZONE},
)
prepared = prepare_fixtures(
    fixtures,
    exclude_youth=settings["exclude_youth"],
    exclude_friendlies=settings["exclude_friendlies"],
)

for key, default in {
    "joya_x_ranking": pd.DataFrame(),
    "joya_x_tables": {},
    "joya_x_all_markets": pd.DataFrame(),
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

c1, c2, c3, c4 = st.columns(4)
c1.metric("Partidos disponibles", len(prepared))
c2.metric("Ligas disponibles", len({(((x.get('league', {}) or {}).get('country') or ''), ((x.get('league', {}) or {}).get('name') or '')) for x in prepared}))
c3.metric("Grupos activos", len(settings["selected_groups"]))
c4.metric("API-Football", "Conectada" if connected else "Sin conexión")

if st.button("🔥 EJECUTAR SPRINT 2", type="primary", use_container_width=True):
    if not settings["selected_groups"]:
        st.error("Selecciona al menos un grupo de mercados.")
    else:
        progress = st.progress(0)
        status_text = st.empty()

        def update_progress(current: int, total: int, league_name: str):
            progress.progress(current / total if total else 1)
            status_text.caption(f"Analizando {current} de {total} · {league_name}")

        with st.spinner("Calculando todos los mercados y sus rankings…"):
            ranking, tables = scan_fixtures(
                fixtures=prepared,
                max_per_league=settings["max_per_league"],
                selected_groups=set(settings["selected_groups"]),
                progress_callback=update_progress,
            )
            all_markets = build_all_market_ranking(ranking, tables)

        st.session_state.joya_x_ranking = ranking
        st.session_state.joya_x_tables = tables
        st.session_state.joya_x_all_markets = all_markets

        for _, summary in ranking.iterrows():
            fixture_id = int(summary["fixture_id"])
            save_analysis_rows(summary.to_dict(), tables.get(fixture_id, pd.DataFrame()))

        progress.empty()
        status_text.empty()
        st.success("Sprint 2 completado: Top 5, explicaciones y rankings generados.")

ranking = st.session_state.joya_x_ranking
tables = st.session_state.joya_x_tables
all_markets = st.session_state.joya_x_all_markets

if ranking.empty or all_markets.empty:
    st.info("Pulsa EJECUTAR SPRINT 2 para iniciar el análisis.")
    st.stop()

tabs = st.tabs([
    "🌍 Top mercados del día",
    "🏆 Top por liga",
    "🥇 Top 5 por partido",
    "📊 Market Matrix completa",
])

with tabs[0]:
    st.subheader("Ranking global real de mercados")
    st.caption("Aquí se comparan todos los mercados analizados, no solo el ganador de cada partido.")

    tiers = st.multiselect(
        "Tiers visibles",
        ["S++", "S+", "A++", "A+", "NO BET"],
        default=["S++", "S+", "A++"],
        key="global_tiers",
    )
    filtered = all_markets[all_markets["Tier"].isin(tiers)] if tiers else all_markets.iloc[0:0]

    st.dataframe(
        filtered[[
            "País", "Liga", "Partido", "Grupo", "Mercado",
            "Probabilidad %", "Confianza JOYA", "Tier", "Riesgo",
            "Calidad", "Consistencia", "Muestra",
        ]].head(100),
        use_container_width=True,
        hide_index=True,
    )

with tabs[1]:
    st.subheader("Top 5 mercados de cada liga")

    for (country, league), _ in ranking.groupby(["País", "Liga"], sort=True):
        top_league = top_markets_by_league(all_markets, country, league, limit=5)
        if top_league.empty:
            continue

        best = top_league.iloc[0]
        with st.expander(
            f"{country} · {league} · 🥇 {best['Mercado']} ({best['Confianza JOYA']:.1f})",
            expanded=False,
        ):
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for index, (_, row) in enumerate(top_league.iterrows()):
                st.markdown(
                    f"### {medals[index]} {row['Mercado']} · {row['Confianza JOYA']:.1f} · {row['Tier']}"
                )
                st.write(f"**Partido:** {row['Partido']}")
                st.write(
                    f"Probabilidad: **{row['Probabilidad %']:.1f}%** · "
                    f"Riesgo: **{row['Riesgo']}** · Calidad: **{row['Calidad']}** · "
                    f"Muestra: **{row['Muestra']}**"
                )
                if index < len(top_league) - 1:
                    st.divider()

with tabs[2]:
    st.subheader("Top 5 mercados por partido")

    for _, match in ranking.sort_values(["País", "Liga", "Confianza"], ascending=[True, True, False]).iterrows():
        fixture_id = int(match["fixture_id"])
        top_match = top_markets_by_match(all_markets, fixture_id, limit=5)
        if top_match.empty:
            continue

        best = top_match.iloc[0]
        label = (
            f"{match['País']} · {match['Liga']} · {match['Local']} vs {match['Visitante']} · "
            f"🏆 {best['Mercado']} ({best['Confianza JOYA']:.1f})"
        )

        with st.expander(label, expanded=False):
            medals = ["🏆", "🥈", "🥉", "4️⃣", "5️⃣"]
            for index, (_, row) in enumerate(top_match.iterrows()):
                st.markdown(
                    f"### {medals[index]} {row['Mercado']} · {row['Confianza JOYA']:.1f} · {row['Tier']}"
                )
                c_a, c_b, c_c, c_d = st.columns(4)
                c_a.metric("Probabilidad", f"{row['Probabilidad %']:.1f}%")
                c_b.metric("Confianza JOYA", f"{row['Confianza JOYA']:.1f}")
                c_c.metric("Riesgo", row["Riesgo"])
                c_d.metric("Muestra", int(row["Muestra"]))

                with st.expander("🔎 ¿Por qué?", expanded=index == 0):
                    for reason in explain_market(row.to_dict()):
                        st.write(f"✓ {reason}")

                if index < len(top_match) - 1:
                    st.divider()

with tabs[3]:
    st.subheader("Todos los mercados por partido")

    for (country, league), league_group in ranking.groupby(["País", "Liga"], sort=True):
        top_league = top_markets_by_league(all_markets, country, league, limit=1)
        if top_league.empty:
            continue
        league_best = top_league.iloc[0]

        with st.expander(
            f"{country} · {league} · Mejor: {league_best['Mercado']} ({league_best['Confianza JOYA']:.1f})",
            expanded=False,
        ):
            st.success(
                f"🏆 Mejor pick de la liga: {league_best['Partido']} · "
                f"{league_best['Mercado']} · Confianza {league_best['Confianza JOYA']:.1f} · "
                f"{league_best['Tier']}"
            )

            for _, match in league_group.iterrows():
                fixture_id = int(match["fixture_id"])
                table = tables.get(fixture_id, pd.DataFrame())
                st.markdown(f"### {match['Local']} vs {match['Visitante']}")

                if table.empty:
                    st.warning("Sin datos suficientes.")
                    continue

                for group_name in settings["selected_groups"]:
                    group_table = get_group_table(table, group_name)
                    if group_table.empty:
                        continue
                    st.markdown(f"**{group_name}**")
                    st.dataframe(group_table, use_container_width=True, hide_index=True)

                st.divider()

st.caption(
    "Los porcentajes son tendencias históricas. La Confianza JOYA aplica calibración por muestra, "
    "consistencia y riesgo; no garantiza resultados."
)
