from __future__ import annotations

import pandas as pd

from core.fragility_engine import (
    bet_status,
    decision_score,
    fragility_for_market,
)


DISPLAY_COLUMNS = [
    "Mercado",
    "Local casa %",
    "Visitante fuera %",
    "Probabilidad %",
    "Confianza JOYA",
    "Fragilidad",
    "Score decisión",
    "Tier",
    "Riesgo",
    "Calidad",
    "Consistencia",
    "Muestra",
    "Estado",
]


def enrich_market_table(table: pd.DataFrame) -> pd.DataFrame:
    if table.empty:
        return pd.DataFrame()

    enriched = table.copy()

    fragility = []
    decision = []
    status = []

    for _, row in enriched.iterrows():
        fragility_label, _ = fragility_for_market(str(row["Mercado"]))
        fragility.append(fragility_label)

        decision.append(
            decision_score(
                float(row["Confianza JOYA"]),
                float(row["Probabilidad %"]),
                int(row["Muestra"]),
                str(row["Mercado"]),
                str(row["Consistencia"]),
            )
        )

        status.append(
            bet_status(
                float(row["Confianza JOYA"]),
                int(row["Muestra"]),
                str(row["Riesgo"]),
                str(row["Calidad"]),
                fragility_label,
                str(row["Consistencia"]),
            )
        )

    enriched["Fragilidad"] = fragility
    enriched["Score decisión"] = decision
    enriched["Estado"] = status

    return enriched.sort_values(
        ["Score decisión", "Confianza JOYA", "Muestra"],
        ascending=[False, False, False],
    )


def explain_market(row: pd.Series) -> list[str]:
    explanations = [
        f"Probabilidad combinada: {float(row['Probabilidad %']):.1f}%.",
        f"Confianza JOYA calibrada: {float(row['Confianza JOYA']):.1f}.",
        f"Local en casa: {float(row['Local casa %']):.1f}%.",
        f"Visitante fuera: {float(row['Visitante fuera %']):.1f}%.",
        f"Muestra utilizada: {int(row['Muestra'])} partidos.",
        f"Consistencia: {row['Consistencia']}.",
        f"Fragilidad del mercado: {row['Fragilidad']}.",
        f"Calidad de datos: {row['Calidad']}.",
        f"Veredicto: {row['Estado']}.",
    ]

    if row["Fragilidad"] in {"Alta", "Muy alta"}:
        explanations.append(
            "Este mercado es sensible a un solo evento y recibe una penalización especial."
        )

    if row["Estado"] == "BET":
        explanations.append(
            "Supera los filtros mínimos de confianza, muestra, consistencia y estabilidad."
        )
    elif row["Estado"] == "BET CON PRECAUCIÓN":
        explanations.append(
            "Tiene respaldo estadístico, pero conserva una fuente relevante de variabilidad."
        )
    else:
        explanations.append(
            "No supera todos los filtros de seguridad del Match Center."
        )

    return explanations


def top_final_picks(enriched: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if enriched.empty:
        return pd.DataFrame(), pd.DataFrame()

    eligible = enriched[
        enriched["Estado"].isin(["BET", "BET CON PRECAUCIÓN"])
    ].copy()

    if eligible.empty:
        return pd.DataFrame(), pd.DataFrame()

    selected = []
    used_groups = set()

    for _, row in eligible.iterrows():
        group = str(row["Grupo"])
        if group in used_groups:
            continue

        selected.append(row)
        used_groups.add(group)

        if len(selected) == 2:
            break

    if len(selected) < 2:
        selected_markets = {str(row["Mercado"]) for row in selected}
        for _, row in eligible.iterrows():
            if str(row["Mercado"]) in selected_markets:
                continue
            selected.append(row)
            if len(selected) == 2:
                break

    top_two = pd.DataFrame(selected)
    used_markets = set(top_two["Mercado"]) if not top_two.empty else set()

    alternative = eligible[
        ~eligible["Mercado"].isin(used_markets)
    ].head(1)

    return top_two, alternative


def family_heatmap(enriched: pd.DataFrame) -> pd.DataFrame:
    if enriched.empty:
        return pd.DataFrame()

    rows = []

    for group, group_table in enriched.groupby("Grupo"):
        best = group_table.sort_values(
            ["Score decisión", "Confianza JOYA"],
            ascending=[False, False],
        ).iloc[0]

        rows.append({
            "Familia": group,
            "Fortaleza": round(float(group_table["Score decisión"].mean()), 1),
            "Mejor mercado": best["Mercado"],
            "Mejor score": best["Score decisión"],
            "Estado dominante": best["Estado"],
        })

    return pd.DataFrame(rows).sort_values(
        "Fortaleza",
        ascending=False,
    )


def market_diversity(enriched: pd.DataFrame) -> dict:
    if enriched.empty:
        return {"strong": [], "weak": []}

    summary = family_heatmap(enriched)

    strong = summary[
        (summary["Fortaleza"] >= 84)
        & (summary["Estado dominante"].isin(["BET", "BET CON PRECAUCIÓN"]))
    ]["Familia"].tolist()

    weak = summary[
        (summary["Fortaleza"] < 76)
        | (summary["Estado dominante"] == "NO BET")
    ]["Familia"].tolist()

    return {"strong": strong, "weak": weak}


def compare_markets(
    enriched: pd.DataFrame,
    market_a: str,
    market_b: str,
) -> dict:
    selected = enriched[
        enriched["Mercado"].isin([market_a, market_b])
    ].copy()

    if len(selected) < 2:
        return {
            "winner": None,
            "loser": None,
            "reason": "No hay datos suficientes.",
        }

    selected = selected.sort_values(
        ["Score decisión", "Confianza JOYA", "Muestra"],
        ascending=[False, False, False],
    )

    winner = selected.iloc[0]
    loser = selected.iloc[1]

    reasons = [
        f"score de decisión {winner['Score decisión']:.1f} vs {loser['Score decisión']:.1f}",
        f"fragilidad {winner['Fragilidad']} vs {loser['Fragilidad']}",
        f"consistencia {winner['Consistencia']} vs {loser['Consistencia']}",
        f"muestra {int(winner['Muestra'])} vs {int(loser['Muestra'])}",
    ]

    return {
        "winner": str(winner["Mercado"]),
        "loser": str(loser["Mercado"]),
        "reason": "; ".join(reasons),
    }
