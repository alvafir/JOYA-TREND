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


def evaluate_markets(home: dict[str, float], away: dict[str, float]) -> pd.DataFrame:
    if not home.get("sample") or not away.get("sample"):
        return pd.DataFrame()

    sample = min(int(home["sample"]), int(away["sample"]))
    rows = [
        ("Más de 1.5 goles", "Total de goles - Más de 1.5",
         average(home["over15_pct"], away["over15_pct"]),
         "Frecuencia reciente de partidos con al menos dos goles."),
        ("Menos de 4.5 goles", "Total de goles - Menos de 4.5",
         average(home["under45_pct"], away["under45_pct"]),
         "Frecuencia reciente de partidos con cuatro goles o menos."),
        ("Ambos anotan", "Ambos equipos marcan - Sí",
         average(home["btts_pct"], away["btts_pct"]),
         "Frecuencia reciente de BTTS."),
        ("Local marca +0.5", "Goles del equipo local - Más de 0.5",
         average(home["score_pct"], away["concede_pct"]),
         "Local anotando y visitante concediendo."),
        ("Visitante marca +0.5", "Goles del equipo visitante - Más de 0.5",
         average(away["score_pct"], home["concede_pct"]),
         "Visitante anotando y local concediendo."),
        ("Local o empate", "Doble oportunidad - 1X",
         round((100 - home["loss_pct"] + away["loss_pct"]) / 2, 1),
         "Local evitando derrotas y visitante perdiendo."),
        ("Visitante o empate", "Doble oportunidad - X2",
         round((100 - away["loss_pct"] + home["loss_pct"]) / 2, 1),
         "Visitante evitando derrotas y local perdiendo."),
    ]

    output = []
    for joya_name, betano_name, score, reason in rows:
        output.append({
            "Mercado JOYA": joya_name,
            "Mercado Betano": betano_name,
            "Score": score,
            "Tier": assign_tier(score, sample),
            "Muestra": sample,
            "Fundamento": reason,
        })

    return pd.DataFrame(output).sort_values("Score", ascending=False)
