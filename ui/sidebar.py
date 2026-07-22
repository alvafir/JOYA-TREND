from __future__ import annotations

from datetime import date, timedelta

import streamlit as st

from config.settings import MARKET_GROUPS


def render_sidebar() -> dict:
    st.sidebar.header("⚙️ Configuración")

    selected_date = st.sidebar.date_input(
        "Fecha",
        value=date.today(),
        min_value=date.today() - timedelta(days=7),
        max_value=date.today() + timedelta(days=30),
    )

    exclude_youth = st.sidebar.checkbox(
        "Excluir juveniles y reservas",
        value=True,
    )

    exclude_friendlies = st.sidebar.checkbox(
        "Excluir amistosos",
        value=False,
    )

    scan_mode = st.sidebar.radio(
        "Cobertura por liga",
        options=["Rápida", "Amplia", "Completa"],
        index=1,
        help=(
            "Rápida analiza hasta 3 partidos por liga; "
            "Amplia hasta 10; Completa analiza todos los partidos disponibles."
        ),
    )

    if scan_mode == "Rápida":
        max_per_league = 3
    elif scan_mode == "Amplia":
        max_per_league = 10
    else:
        max_per_league = 999

    st.sidebar.caption(
        "Para ligas con muchos partidos, como MLS, usa Cobertura completa."
    )

    selected_groups = st.sidebar.multiselect(
        "Mercados activos",
        options=list(MARKET_GROUPS.keys()),
        default=list(MARKET_GROUPS.keys()),
    )

    st.sidebar.divider()
    st.sidebar.subheader("🌙 Soñadora")

    dream_min_confidence = st.sidebar.slider(
        "Confianza mínima",
        min_value=70,
        max_value=95,
        value=79,
        step=1,
    )

    dream_min_sample = st.sidebar.slider(
        "Muestra mínima",
        min_value=5,
        max_value=12,
        value=6,
        step=1,
    )

    dream_picks = st.sidebar.slider(
        "Cantidad de picks",
        min_value=2,
        max_value=5,
        value=3,
        step=1,
    )

    return {
        "date": selected_date,
        "exclude_youth": exclude_youth,
        "exclude_friendlies": exclude_friendlies,
        "max_per_league": int(max_per_league),
        "scan_mode": scan_mode,
        "selected_groups": selected_groups,
        "dream_min_confidence": int(dream_min_confidence),
        "dream_min_sample": int(dream_min_sample),
        "dream_picks": int(dream_picks),
    }
