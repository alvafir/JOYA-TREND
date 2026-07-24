from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.decision_engine import verdict_for_match
from modules.ranking_engine import top_markets_by_match


def render_match_verdicts(ranking: pd.DataFrame, all_markets: pd.DataFrame) -> None:
    st.subheader("🎯 Veredicto automático por partido")

    ordered = ranking.sort_values(["País", "Liga", "Confianza"], ascending=[True, True, False])

    for _, match in ordered.iterrows():
        fixture_id = int(match["fixture_id"])
        full_match = all_markets[all_markets["fixture_id"] == fixture_id].copy()
        top_match = top_markets_by_match(all_markets, fixture_id, limit=10)
        verdict = verdict_for_match(pd.concat([top_match, full_match[full_match["Tier"] == "NO BET"]]).drop_duplicates())

        principal = verdict.get("principal")
        label_pick = principal["Mercado"] if principal else "NO BET"

        with st.expander(
            f"{match['País']} · {match['Liga']} · {match['Local']} vs {match['Visitante']} · {label_pick}",
            expanded=False,
        ):
            if verdict["status"] == "APTO PARA CARTILLA":
                st.success(f"✅ {verdict['status']}")
            elif verdict["status"] == "APTO CON PRECAUCIÓN":
                st.warning(f"⚠️ {verdict['status']}")
            else:
                st.error(f"⛔ {verdict['status']}")

            if principal:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Pick principal", principal["Mercado"])
                c2.metric("Confianza", f"{principal['Confianza JOYA']:.1f}")
                c3.metric("Tier", principal["Tier"])
                c4.metric("Riesgo", principal["Riesgo"])

            alternative = verdict.get("alternative")
            avoid = verdict.get("avoid")

            if alternative:
                st.info(
                    f"🥈 Alternativa: {alternative['Mercado']} · "
                    f"Confianza {alternative['Confianza JOYA']:.1f} · {alternative['Tier']}"
                )
            if avoid:
                st.error(
                    f"🚫 Mercado a evitar: {avoid['Mercado']} · "
                    f"Confianza {avoid['Confianza JOYA']:.1f} · Riesgo {avoid['Riesgo']}"
                )

            st.write(verdict["reason"])
