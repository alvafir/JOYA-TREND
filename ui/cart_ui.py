from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.cart_builder import build_smart_cart


def render_cart_builder(all_markets: pd.DataFrame) -> None:
    st.subheader("💚 Constructor Inteligente FULL KII")
    st.caption(
        "JOYA elige mercados de alta confianza y evita repetir partidos, ligas, países y familias de mercado."
    )

    c1, c2, c3 = st.columns(3)
    min_confidence = c1.slider("Confianza mínima", 75.0, 99.0, 85.0, 0.5)
    max_picks = c2.slider("Máximo de picks", 2, 10, 4)
    target_odds = c3.number_input(
        "Cuota objetivo (opcional)", min_value=0.0, value=0.0, step=0.10,
        help="Para usar cuota objetivo debes ingresar cuotas manuales en la tabla inferior."
    )

    c4, c5, c6, c7 = st.columns(4)
    max_per_league = c4.selectbox("Máximo por liga", [1, 2, 3], index=0)
    max_per_country = c5.selectbox("Máximo por país", [1, 2, 3], index=0)
    max_same_market = c6.selectbox("Repetir mercado", [1, 2, 3], index=0)
    max_same_family = c7.selectbox("Repetir familia", [1, 2, 3], index=1)

    allowed_tiers = st.multiselect(
        "Tiers permitidos",
        ["S++", "S+", "A++", "A+"],
        default=["S++", "S+", "A++"],
    )

    odds_candidates = all_markets[
        (all_markets["Confianza JOYA"] >= min_confidence)
        & (all_markets["Tier"].isin(allowed_tiers))
    ].head(80).copy()

    odds_candidates["Cuota"] = 0.0
    odds_input = st.data_editor(
        odds_candidates[["fixture_id", "País", "Liga", "Partido", "Mercado", "Confianza JOYA", "Cuota"]],
        use_container_width=True,
        hide_index=True,
        disabled=["fixture_id", "País", "Liga", "Partido", "Mercado", "Confianza JOYA"],
        column_config={
            "Cuota": st.column_config.NumberColumn("Cuota Betano/manual", min_value=0.0, step=0.01),
        },
        key="manual_odds_editor",
    )

    manual_odds = {
        (int(row["fixture_id"]), str(row["Mercado"])): float(row["Cuota"])
        for _, row in odds_input.iterrows()
        if float(row["Cuota"]) > 1.0
    }

    if st.button("💚 GENERAR CARTILLA FULL KII", type="primary", use_container_width=True):
        cart, meta = build_smart_cart(
            all_markets=all_markets,
            min_confidence=min_confidence,
            allowed_tiers=tuple(allowed_tiers),
            max_picks=max_picks,
            max_per_league=max_per_league,
            max_per_country=max_per_country,
            max_same_market=max_same_market,
            max_same_family=max_same_family,
            avoid_same_fixture=True,
            manual_odds=manual_odds,
            target_odds=target_odds if target_odds > 1 else None,
        )

        if cart.empty:
            st.warning(meta.get("reason", "No fue posible crear la cartilla."))
            return

        st.success("Cartilla FULL KII generada")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Picks", len(cart))
        m2.metric("Confianza promedio", f"{meta['average_confidence']:.1f}")
        m3.metric("Correlación", meta["correlation"])
        m4.metric("Cuota combinada", f"{meta['combined_odds']:.2f}" if meta["combined_odds"] else "Sin cuotas")

        display_columns = [
            "País", "Liga", "Partido", "Grupo", "Mercado",
            "Probabilidad %", "Confianza JOYA", "Tier", "Riesgo", "Cuota",
        ]
        st.dataframe(cart[display_columns], use_container_width=True, hide_index=True)

        st.caption(
            f"Probabilidad estadística combinada aproximada: {meta['combined_probability']:.2f}%. "
            "Este cálculo asume independencia y debe interpretarse con cautela."
        )

        if meta["warnings"]:
            st.warning("Se detectaron relaciones que conviene revisar:")
            for warning in meta["warnings"]:
                st.write(f"• {warning}")
        else:
            st.success("No se detectaron correlaciones altas entre los picks seleccionados.")
