from __future__ import annotations

import pandas as pd


def average(a: float, b: float) -> float:
    return round((a + b) / 2, 1)


def assign_tier(score: float, sample: int) -> str:
    if sample < 6:
        return "NO BET"
    if score >= 88:
        return "S++"
    if score >= 82:
        return "S+"
    if score >= 76:
        return "A++"
    return "NO BET"


def evaluate_markets(
    home: dict[str, float],
    away: dict[str, float],
) -> pd.DataFrame:
    if not home.get("sample") or not away.get("sample"):
        return pd.DataFrame()

    min_sample = min(int(home["sample"]), int(away["sample"]))

    rows = [
        {
            "Mercado JOYA": "Más de 1.5 goles",
            "Mercado Betano": "Total de goles - Más de 1.5",
            "Score": average(home["over15_pct"], away["over15_pct"]),
            "Fundamento": "Frecuencia reciente de partidos con al menos dos goles.",
        },
        {
            "Mercado JOYA": "Menos de 4.5 goles",
            "Mercado Betano": "Total de goles - Menos de 4.5",
            "Score": average(home["under45_pct"], away["under45_pct"]),
            "Fundamento": "Frecuencia reciente de partidos con cuatro goles o menos.",
        },
        {
            "Mercado JOYA": "Ambos anotan",
            "Mercado Betano": "Ambos equipos marcan - Sí",
            "Score": average(home["btts_pct"], away["btts_pct"]),
            "Fundamento": "Frecuencia reciente de BTTS en ambos equipos.",
        },
        {
            "Mercado JOYA": "Local marca +0.5",
            "Mercado Betano": "Goles del equipo local - Más de 0.5",
            "Score": average(home["score_pct"], away["concede_pct"]),
            "Fundamento": "Local anotando y visitante concediendo.",
        },
        {
            "Mercado JOYA": "Visitante marca +0.5",
            "Mercado Betano": "Goles del equipo visitante - Más de 0.5",
            "Score": average(away["score_pct"], home["concede_pct"]),
            "Fundamento": "Visitante anotando y local concediendo.",
        },
        {
            "Mercado JOYA": "Local o empate",
            "Mercado Betano": "Doble oportunidad - 1X",
            "Score": round((100 - home["loss_pct"] + away["loss_pct"]) / 2, 1),
            "Fundamento": "Local evitando derrotas y visitante perdiendo.",
        },
        {
            "Mercado JOYA": "Visitante o empate",
            "Mercado Betano": "Doble oportunidad - X2",
            "Score": round((100 - away["loss_pct"] + home["loss_pct"]) / 2, 1),
            "Fundamento": "Visitante evitando derrotas y local perdiendo.",
        },
    ]

    for row in rows:
        row["Tier"] = assign_tier(float(row["Score"]), min_sample)
        row["Muestra"] = min_sample

    return pd.DataFrame(rows).sort_values("Score", ascending=False)
