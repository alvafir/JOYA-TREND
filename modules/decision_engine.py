from __future__ import annotations

import pandas as pd


def verdict_for_match(top_match: pd.DataFrame) -> dict:
    if top_match.empty:
        return {
            "status": "NO BET",
            "principal": None,
            "alternative": None,
            "avoid": None,
            "level": "NO BET",
            "reason": "No hay mercados con muestra y confianza suficientes.",
        }

    ordered = top_match.sort_values(
        ["Confianza JOYA", "Muestra", "Probabilidad %"],
        ascending=[False, False, False],
    )
    principal = ordered.iloc[0]
    alternative = ordered.iloc[1] if len(ordered) > 1 else None

    avoid_candidates = ordered[
        (ordered["Tier"] == "NO BET") | (ordered["Riesgo"] == "Alto")
    ]
    avoid = avoid_candidates.iloc[-1] if not avoid_candidates.empty else None

    confidence = float(principal["Confianza JOYA"])
    risk = str(principal["Riesgo"])
    quality = str(principal["Calidad"])

    if confidence >= 90 and risk == "Bajo" and quality in {"A+", "A"}:
        status = "APTO PARA CARTILLA"
    elif confidence >= 85 and risk in {"Bajo", "Medio"}:
        status = "APTO CON PRECAUCIÓN"
    else:
        status = "NO BET"

    return {
        "status": status,
        "principal": principal.to_dict(),
        "alternative": alternative.to_dict() if alternative is not None else None,
        "avoid": avoid.to_dict() if avoid is not None else None,
        "level": str(principal["Tier"]),
        "reason": (
            f"El mercado principal lidera el partido con {confidence:.1f} de confianza, "
            f"riesgo {risk.lower()}, calidad {quality} y muestra {int(principal['Muestra'])}."
        ),
    }
