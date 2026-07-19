from __future__ import annotations

import pandas as pd
import streamlit as st


def show_ranking(ranking: pd.DataFrame) -> None:
    if ranking.empty:
        st.warning("El scanner no encontró candidatos con datos suficientes.")
        return

    st.subheader("🏆 Ranking JOYA")
    st.dataframe(
        ranking[
            [
                "País",
                "Liga",
                "Local",
                "Visitante",
                "Pick",
                "JOYA Score",
                "Tier",
                "Muestra",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )


def show_cart(cart: pd.DataFrame, combined_odds: float, target: float) -> None:
    if cart.empty:
        st.warning("No hay suficientes selecciones para crear la cartilla.")
        return

    if combined_odds < target:
        st.warning(
            f"La cartilla más segura alcanzó una cuota estimada de {combined_odds:.2f}, "
            f"por debajo del objetivo {target:.2f}. No se forzaron picks."
        )
    else:
        st.success(f"Cartilla creada · cuota estimada {combined_odds:.2f}")

    st.dataframe(
        cart[["Local", "Visitante", "Pick", "JOYA Score", "Tier"]],
        use_container_width=True,
        hide_index=True,
    )
