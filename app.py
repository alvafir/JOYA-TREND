from __future__ import annotations

import pandas as pd
import streamlit as st

from api.football_api import api_list, get_api_key, test_connection
from config.settings import DEFAULT_TIMEZONE
from database.database import initialize_database
from history.joya_brain import save_analysis_rows
from modules.intelligence_center import (
    DISPLAY_COLUMNS,
    compare_markets,
    enrich_market_table,
    explain_market,
    family_heatmap,
    market_diversity,
    top_final_picks,
)
from modules.league_analyzer import build_league_ranking
from modules.scanner import scan_fixtures
# Hotfix v1.0.1:
# Intenta cargar Strategy Center. Si GitHub/Streamlit conserva un archivo antiguo,
# la app usa estas funciones locales y evita que toda la aplicación se caiga.
try:
    from modules.strategy_center import (
        bleeding_core,
        build_dream_card,
        dream_candidates,
        flatten_markets,
        joya_of_day,
        ladder,
        safe_alternative,
        trap_reasons,
    )
except (ImportError, ModuleNotFoundError):
    from config.settings import DREAM_MARKETS, SAFE_ALTERNATIVES

    def flatten_markets(ranking, market_tables):
        if ranking is None or ranking.empty:
            return pd.DataFrame()
        rows = []
        for _, match in ranking.iterrows():
            fixture_id = int(match["fixture_id"])
            table = market_tables.get(fixture_id, pd.DataFrame())
            if table is None or table.empty:
                continue
            for _, market in table.iterrows():
                row = market.to_dict()
                row.update({
                    "fixture_id": fixture_id,
                    "País": match["País"],
                    "Liga": match["Liga"],
                    "Local": match["Local"],
                    "Visitante": match["Visitante"],
                    "Partido": f"{match['Local']} vs {match['Visitante']}",
                })
                rows.append(row)
        return pd.DataFrame(rows)

    def dream_candidates(all_markets, min_confidence=79, min_sample=6):
        if all_markets.empty:
            return pd.DataFrame()
        df = all_markets[
            all_markets["Mercado"].isin(DREAM_MARKETS)
            & (all_markets["Confianza JOYA"] >= min_confidence)
            & (all_markets["Muestra"] >= min_sample)
            & all_markets["Calidad"].isin(["A+", "A", "B+"])
        ].copy()
        if df.empty:
            return df
        risk_penalty = df["Riesgo"].map(
            {"Bajo": 0, "Medio": 3, "Alto": 8}
        ).fillna(8)
        df["Potencial soñadora"] = (
            df["Confianza JOYA"]
            + df["Probabilidad %"] * 0.15
            - risk_penalty
        ).round(1)
        return df.sort_values(
            ["Potencial soñadora", "Confianza JOYA", "Muestra"],
            ascending=[False, False, False],
        )

    def build_dream_card(candidates, picks=3):
        if candidates.empty:
            return pd.DataFrame()
        selected, matches, leagues = [], set(), set()
        for _, row in candidates.iterrows():
            league_key = (row["País"], row["Liga"])
            if row["fixture_id"] in matches or league_key in leagues:
                continue
            selected.append(row)
            matches.add(row["fixture_id"])
            leagues.add(league_key)
            if len(selected) >= picks:
                break
        return pd.DataFrame(selected)

    def joya_of_day(all_markets):
        if all_markets.empty:
            return pd.DataFrame()
        df = all_markets[
            all_markets["Tier"].isin(["S++", "S+"])
            & (all_markets["Riesgo"] == "Bajo")
            & (all_markets["Muestra"] >= 8)
        ]
        return df.sort_values(
            ["Confianza JOYA", "Muestra"],
            ascending=[False, False],
        ).head(1)

    def bleeding_core(all_markets, max_picks=8):
        if all_markets.empty:
            return pd.DataFrame()
        df = all_markets[
            all_markets["Tier"].isin(["S++", "S+", "A++"])
            & all_markets["Riesgo"].isin(["Bajo", "Medio"])
        ].sort_values(
            ["Confianza JOYA", "Muestra"],
            ascending=[False, False],
        )
        selected, matches = [], set()
        for _, row in df.iterrows():
            if row["fixture_id"] in matches:
                continue
            selected.append(row)
            matches.add(row["fixture_id"])
            if len(selected) >= max_picks:
                break
        return pd.DataFrame(selected)

    def ladder(all_markets):
        empty = {
            "Nivel 1 · Base": pd.DataFrame(),
            "Nivel 2 · Intermedio": pd.DataFrame(),
            "Nivel 3 · Soñador": pd.DataFrame(),
        }
        if all_markets.empty:
            return empty
        df = all_markets[
            all_markets["Tier"].isin(["S++", "S+", "A++"])
            & all_markets["Riesgo"].isin(["Bajo", "Medio"])
        ].sort_values(
            ["Confianza JOYA", "Muestra"],
            ascending=[False, False],
        )

        def choose(n):
            chosen, matches, leagues = [], set(), set()
            for _, row in df.iterrows():
                league_key = (row["País"], row["Liga"])
                if row["fixture_id"] in matches or league_key in leagues:
                    continue
                chosen.append(row)
                matches.add(row["fixture_id"])
                leagues.add(league_key)
                if len(chosen) >= n:
                    break
            return pd.DataFrame(chosen)

        return {
            "Nivel 1 · Base": choose(2),
            "Nivel 2 · Intermedio": choose(3),
            "Nivel 3 · Soñador": choose(4),
        }

    def safe_alternative(market):
        return SAFE_ALTERNATIVES.get(
            market,
            "Usar la alternativa conservadora mejor puntuada",
        )

    def trap_reasons(row):
        reasons = []
        if row["Muestra"] < 6:
            reasons.append("Muestra pequeña")
        if row["Consistencia"] == "Baja":
            reasons.append("Tendencias local/visitante divididas")
        if row["Riesgo"] == "Alto":
            reasons.append("Riesgo alto")
        if abs(row["Local casa %"] - row["Visitante fuera %"]) >= 25:
            reasons.append("Señales muy desiguales")
        if row["Probabilidad %"] >= 88 and row["Confianza JOYA"] < 82:
            reasons.append(
                "Porcentaje bruto alto, pero confianza calibrada baja"
            )
        if (
            row["Mercado"] in {"Gana local", "Gana visitante"}
            and row["Confianza JOYA"] < 82
        ):
            reasons.append("Ganador simple sin ventaja suficiente")
        return reasons
from ui.sidebar import render_sidebar
from utils.filters import prepare_fixtures


st.set_page_config(
    page_title="JOYA X Enterprise",
    page_icon="💎",
    layout="wide",
)

initialize_database()

st.title("💎 JOYA X ENTERPRISE")
st.caption(
    "v1.0.3 Full League Scan · Intelligence Center · Match Report · JOYA Explain · Heatmap · Top 2"
)

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

# Valores de respaldo para compatibilidad con configuraciones antiguas.
settings.setdefault("dream_min_confidence", 79)
settings.setdefault("dream_min_sample", 6)
settings.setdefault("dream_picks", 3)
settings.setdefault("selected_groups", [])
settings.setdefault("max_per_league", 10)
settings.setdefault("scan_mode", "Amplia")
settings.setdefault("exclude_youth", True)
settings.setdefault("exclude_friendlies", False)

fixtures = api_list(
    "fixtures",
    {
        "date": settings["date"].isoformat(),
        "timezone": DEFAULT_TIMEZONE,
    },
)

prepared = prepare_fixtures(
    fixtures,
    exclude_youth=settings["exclude_youth"],
    exclude_friendlies=settings["exclude_friendlies"],
)

if "joya_x_ranking" not in st.session_state:
    st.session_state.joya_x_ranking = pd.DataFrame()

if "joya_x_tables" not in st.session_state:
    st.session_state.joya_x_tables = {}

c1, c2, c3, c4 = st.columns(4)

c1.metric("Partidos disponibles", len(prepared))
c2.metric(
    "Ligas disponibles",
    len({
        (
            ((item.get("league", {}) or {}).get("country") or ""),
            ((item.get("league", {}) or {}).get("name") or ""),
        )
        for item in prepared
    }),
)
c3.metric("Cobertura", settings.get("scan_mode", "Amplia"))
c4.metric("API-Football", "Conectada")

if settings.get("scan_mode") == "Completa":
    st.info(
        "🔎 Cobertura completa activada: JOYA analizará todos los partidos "
        "disponibles de cada liga. Esto puede consumir más solicitudes de API-Football."
    )

if st.button(
    "🧠 EJECUTAR INTELLIGENCE CENTER",
    type="primary",
    use_container_width=True,
):
    if not settings["selected_groups"]:
        st.error("Selecciona al menos una familia de mercados.")
    else:
        progress = st.progress(0)
        status_text = st.empty()

        def update_progress(current, total, league_name):
            progress.progress(current / total if total else 1)
            status_text.caption(
                f"Analizando {current} de {total} · {league_name}"
            )

        with st.spinner("Construyendo informes inteligentes por partido…"):
            ranking, tables = scan_fixtures(
                prepared,
                settings["max_per_league"],
                set(settings["selected_groups"]),
                update_progress,
            )

        st.session_state.joya_x_ranking = ranking
        st.session_state.joya_x_tables = tables

        for _, summary in ranking.iterrows():
            fixture_id = int(summary["fixture_id"])
            save_analysis_rows(
                summary.to_dict(),
                tables.get(fixture_id, pd.DataFrame()),
            )

        progress.empty()
        status_text.empty()
        st.success("Intelligence Center completado.")

ranking = st.session_state.joya_x_ranking
tables = st.session_state.joya_x_tables

if ranking.empty:
    st.info("Pulsa EJECUTAR INTELLIGENCE CENTER.")
    st.stop()

all_markets = flatten_markets(ranking, tables)

tabs = st.tabs([
    "🧠 Intelligence Center",
    "💎 Joya del día",
    "🌙 Soñadora",
    "🩸 Núcleo",
    "📈 Escalera",
    "⚠️ Trampas",
    "🏆 Ranking global",
    "🌍 Por liga",
])

with tabs[0]:
    st.subheader("🧠 Match Report completo")

    for (country, league), league_group in ranking.groupby(
        ["País", "Liga"],
        sort=True,
    ):
        with st.expander(f"{country} · {league}", expanded=False):
            for _, match in league_group.iterrows():
                fixture_id = int(match["fixture_id"])
                raw_table = tables.get(fixture_id, pd.DataFrame())

                st.markdown(
                    f"## {match['Local']} vs {match['Visitante']}"
                )

                if raw_table.empty:
                    st.warning("Sin datos suficientes.")
                    st.divider()
                    continue

                enriched = enrich_market_table(raw_table)
                heatmap = family_heatmap(enriched)
                diversity = market_diversity(enriched)

                st.markdown("### 🌡️ Heatmap de familias")

                if not heatmap.empty:
                    heatmap_columns = st.columns(min(4, len(heatmap)))

                    for index, (_, family) in enumerate(
                        heatmap.head(4).iterrows()
                    ):
                        with heatmap_columns[index]:
                            st.metric(
                                str(family["Familia"]),
                                f"{float(family['Fortaleza']):.1f}",
                                str(family["Mejor mercado"]),
                            )

                    st.dataframe(
                        heatmap,
                        use_container_width=True,
                        hide_index=True,
                    )

                st.markdown("### 🧩 Diversidad de mercados")

                strong_text = (
                    ", ".join(diversity["strong"])
                    if diversity["strong"]
                    else "Ninguna familia claramente dominante"
                )
                weak_text = (
                    ", ".join(diversity["weak"])
                    if diversity["weak"]
                    else "Sin familias claramente débiles"
                )

                d1, d2 = st.columns(2)
                d1.success(f"✅ Familias fuertes: {strong_text}")
                d2.warning(f"⚠️ Familias débiles: {weak_text}")

                st.markdown("### 📊 Matriz completa")

                for group_name in settings["selected_groups"]:
                    group_table = enriched[
                        enriched["Grupo"] == group_name
                    ].copy()

                    if group_table.empty:
                        continue

                    st.markdown(f"#### {group_name}")

                    st.dataframe(
                        group_table[DISPLAY_COLUMNS],
                        use_container_width=True,
                        hide_index=True,
                    )

                    market_to_explain = st.selectbox(
                        f"¿Por qué? · {group_name}",
                        group_table["Mercado"].tolist(),
                        key=f"explain_{fixture_id}_{group_name}",
                    )

                    selected_row = group_table[
                        group_table["Mercado"] == market_to_explain
                    ].iloc[0]

                    with st.expander(
                        f"🧠 JOYA Explain: {market_to_explain}",
                        expanded=False,
                    ):
                        for explanation in explain_market(selected_row):
                            st.write(f"✓ {explanation}")

                st.markdown("### 🏆 Top final del partido")

                top_two, alternative = top_final_picks(enriched)

                if top_two.empty:
                    st.error(
                        "NO BET: el partido no presenta suficientes mercados estables."
                    )
                else:
                    pick_columns = st.columns(2)

                    for position, (_, pick) in enumerate(
                        top_two.iterrows(),
                        start=1,
                    ):
                        with pick_columns[position - 1]:
                            medal = "🥇" if position == 1 else "🥈"
                            st.success(
                                f"{medal} PICK #{position}\n\n"
                                f"**{pick['Mercado']}**\n\n"
                                f"Confianza: **{pick['Confianza JOYA']:.1f}**\n\n"
                                f"Score decisión: **{pick['Score decisión']:.1f}**\n\n"
                                f"Fragilidad: **{pick['Fragilidad']}**\n\n"
                                f"Estado: **{pick['Estado']}**\n\n"
                                f"Muestra: **{int(pick['Muestra'])}**"
                            )

                    if not alternative.empty:
                        pick = alternative.iloc[0]
                        st.info(
                            f"🥉 Alternativa: **{pick['Mercado']}** · "
                            f"Confianza {pick['Confianza JOYA']:.1f} · "
                            f"Score {pick['Score decisión']:.1f} · "
                            f"Fragilidad {pick['Fragilidad']} · "
                            f"{pick['Estado']}"
                        )

                st.markdown("### ⚖️ Comparador de mercados")

                options = enriched["Mercado"].tolist()

                if len(options) >= 2:
                    compare_columns = st.columns(2)

                    market_a = compare_columns[0].selectbox(
                        "Mercado A",
                        options,
                        key=f"compare_a_{fixture_id}",
                    )

                    market_b = compare_columns[1].selectbox(
                        "Mercado B",
                        options,
                        index=1,
                        key=f"compare_b_{fixture_id}",
                    )

                    if market_a == market_b:
                        st.warning("Selecciona dos mercados diferentes.")
                    else:
                        result = compare_markets(
                            enriched,
                            market_a,
                            market_b,
                        )

                        if result["winner"]:
                            st.info(
                                f"JOYA prefiere **{result['winner']}** sobre "
                                f"**{result['loser']}**: {result['reason']}."
                            )

                st.divider()

with tabs[1]:
    st.subheader("💎 Joya del día")
    joya = joya_of_day(all_markets)

    if joya.empty:
        st.warning("No existe una Joya del día suficientemente respaldada.")
    else:
        st.dataframe(
            joya[[
                "País",
                "Liga",
                "Partido",
                "Mercado",
                "Probabilidad %",
                "Confianza JOYA",
                "Tier",
                "Riesgo",
                "Calidad",
                "Consistencia",
                "Muestra",
            ]],
            use_container_width=True,
            hide_index=True,
        )

with tabs[2]:
    st.subheader("🌙 Soñadora del día")

    candidates = dream_candidates(
        all_markets,
        settings["dream_min_confidence"],
        settings["dream_min_sample"],
    )

    dream = build_dream_card(
        candidates,
        settings["dream_picks"],
    )

    if dream.empty or len(dream) < 2:
        st.warning(
            "Hoy no existe una Soñadora suficientemente respaldada."
        )
    else:
        for index, (_, row) in enumerate(dream.iterrows(), start=1):
            st.markdown(
                f"### {index}. {row['Partido']} — {row['Mercado']}\n"
                f"**Confianza:** {row['Confianza JOYA']:.1f} · "
                f"**Probabilidad:** {row['Probabilidad %']:.1f}% · "
                f"**Alternativa segura:** {safe_alternative(row['Mercado'])}"
            )

with tabs[3]:
    st.subheader("🩸 Núcleo sangrado")
    core = bleeding_core(all_markets)

    if core.empty:
        st.warning("No hay selecciones suficientes.")
    else:
        st.dataframe(
            core[[
                "País",
                "Liga",
                "Partido",
                "Mercado",
                "Confianza JOYA",
                "Tier",
                "Riesgo",
                "Calidad",
                "Muestra",
            ]],
            use_container_width=True,
            hide_index=True,
        )

with tabs[4]:
    st.subheader("📈 Escalera automática")

    for name, table in ladder(all_markets).items():
        st.markdown(f"### {name}")

        if table.empty:
            st.warning("Sin selecciones suficientes.")
        else:
            st.dataframe(
                table[[
                    "País",
                    "Liga",
                    "Partido",
                    "Mercado",
                    "Confianza JOYA",
                    "Tier",
                    "Riesgo",
                    "Muestra",
                ]],
                use_container_width=True,
                hide_index=True,
            )

with tabs[5]:
    st.subheader("⚠️ Detector de trampas")

    trap_rows = []

    for _, row in all_markets.iterrows():
        reasons = trap_reasons(row)

        if reasons:
            trap_rows.append({
                "País": row["País"],
                "Liga": row["Liga"],
                "Partido": row["Partido"],
                "Mercado": row["Mercado"],
                "Confianza": row["Confianza JOYA"],
                "Riesgo": row["Riesgo"],
                "Alerta": " · ".join(reasons),
                "Alternativa": safe_alternative(row["Mercado"]),
            })

    traps = pd.DataFrame(trap_rows)

    if traps.empty:
        st.success("No se detectaron trampas relevantes.")
    else:
        st.dataframe(
            traps,
            use_container_width=True,
            hide_index=True,
        )

with tabs[6]:
    st.subheader("🏆 Ranking global ajustado")

    enriched_global = []

    for fixture_id, table in tables.items():
        match = ranking[ranking["fixture_id"] == fixture_id]
        if match.empty:
            continue

        match_info = match.iloc[0]
        enriched = enrich_market_table(table)

        for _, market in enriched.iterrows():
            row = market.to_dict()
            row.update({
                "País": match_info["País"],
                "Liga": match_info["Liga"],
                "Partido": (
                    f"{match_info['Local']} vs {match_info['Visitante']}"
                ),
            })
            enriched_global.append(row)

    global_table = pd.DataFrame(enriched_global)

    if not global_table.empty:
        st.dataframe(
            global_table.sort_values(
                ["Score decisión", "Confianza JOYA", "Muestra"],
                ascending=[False, False, False],
            )[[
                "País",
                "Liga",
                "Partido",
                "Grupo",
                "Mercado",
                "Probabilidad %",
                "Confianza JOYA",
                "Fragilidad",
                "Score decisión",
                "Estado",
                "Tier",
                "Riesgo",
                "Calidad",
                "Consistencia",
                "Muestra",
            ]].head(200),
            use_container_width=True,
            hide_index=True,
        )

with tabs[7]:
    st.subheader("🌍 Mejor mercado por liga")
    st.dataframe(
        build_league_ranking(ranking),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "JOYA Intelligence Center penaliza mercados frágiles y muestra dos picks "
    "finales por partido. BET, BET CON PRECAUCIÓN y NO BET son clasificaciones "
    "estadísticas, no garantías."
)
