from __future__ import annotations
import pandas as pd
import streamlit as st


DISPLAY_COLUMNS = [
    "Local", "Visitante", "Pick", "JOYA Score", "Tier", "Muestra"
]


def show_catalog_by_league(catalog: pd.DataFrame) -> None:
    if catalog.empty:
        st.info("No hay partidos disponibles.")
        return

    st.subheader("🌍 Ligas disponibles en la cartelera")
    st.caption(
        f"{catalog['Liga'].nunique()} ligas · {len(catalog)} partidos antes del análisis"
    )

    for (country, league), group in catalog.groupby(["País", "Liga"], sort=True):
        with st.expander(f"{country} · {league} ({len(group)} partidos)"):
            st.dataframe(
                group[["Local", "Visitante", "Hora API"]],
                use_container_width=True,
                hide_index=True,
            )


def show_ranking_by_league(ranking: pd.DataFrame) -> None:
    if ranking.empty:
        st.warning("El scanner no encontró candidatos con datos suficientes.")
        return

    st.subheader("🏆 Resultados separados por liga")
    st.caption(
        f"{ranking['Liga'].nunique()} ligas analizadas · {len(ranking)} candidatos"
    )

    countries = ["Todos"] + sorted(ranking["País"].dropna().unique().tolist())
    selected_country = st.selectbox("Filtrar resultados por país", countries)

    visible = ranking if selected_country == "Todos" else ranking[ranking["País"] == selected_country]

    for (country, league), group in visible.groupby(["País", "Liga"], sort=True):
        best_score = group["JOYA Score"].max()
        with st.expander(
            f"{country} · {league} · {len(group)} picks · mejor score {best_score:.1f}",
            expanded=False,
        ):
            st.dataframe(
                group[DISPLAY_COLUMNS],
                use_container_width=True,
                hide_index=True,
            )


def show_cart(cart: pd.DataFrame, combined_odds: float, target: float) -> None:
    if cart.empty:
        st.warning("No hay suficientes selecciones para crear la cartilla.")
        return

    if combined_odds < target:
        st.warning(
            f"La selección más segura alcanzó cuota estimada {combined_odds:.2f}, "
            f"por debajo del objetivo {target:.2f}. JOYA no forzó picks."
        )
    else:
        st.success(f"Cartilla creada · cuota estimada {combined_odds:.2f}")

    st.dataframe(
        cart[["País", "Liga"] + DISPLAY_COLUMNS],
        use_container_width=True,
        hide_index=True,
    )
