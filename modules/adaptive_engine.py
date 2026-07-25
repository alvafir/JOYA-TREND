from __future__ import annotations

import pandas as pd


def priority_level(confidence: float, sample: int, risk: str) -> str:
    if confidence >= 92 and sample >= 8 and risk == "Bajo":
        return "Nivel 1 · Interés alto"
    if confidence >= 85 and sample >= 6 and risk in {"Bajo", "Medio"}:
        return "Nivel 2 · Interés medio"
    if confidence >= 80 and sample >= 5:
        return "Nivel 3 · Interés bajo"
    return "NO BET"


def add_priority(ranking: pd.DataFrame) -> pd.DataFrame:
    if ranking is None or ranking.empty:
        return pd.DataFrame() if ranking is None else ranking
    if not {'Confianza', 'Muestra', 'Riesgo'}.issubset(ranking.columns):
        return ranking.copy()

    result = ranking.copy()
    result["Prioridad"] = result.apply(
        lambda row: priority_level(
            float(row["Confianza"]),
            int(row["Muestra"]),
            str(row["Riesgo"]),
        ),
        axis=1,
    )
    return result


def automatic_deep_limit(mode: str, total_matches: int) -> int:
    mapping = {
        "Solo resumen": 0,
        "Top 5 partidos": 5,
        "Top 10 partidos": 10,
        "Todos": total_matches,
    }
    return mapping.get(mode, 5)


def performance_note(mode: str) -> str:
    notes = {
        "Rápido": (
            "Escaneo ligero activo. Mercados principales y rangos cargan primero; "
            "córners, tarjetas y remates quedan bajo demanda."
        ),
        "Equilibrado": (
            "Equilibra velocidad y detalle. Recomendado para jornadas medianas."
        ),
        "Profundo": (
            "Máximo detalle. Puede consumir muchas solicitudes y tardar más."
        ),
    }
    return notes.get(mode, notes["Rápido"])
