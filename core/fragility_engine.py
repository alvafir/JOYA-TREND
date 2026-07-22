from __future__ import annotations

FRAGILITY_RULES = {
    "Sin gol antes del 10": ("Alta", 18),
    "Sin gol 0-10 + gol antes del 70": ("Muy alta", 25),
    "Local marca primero": ("Alta", 15),
    "Visitante marca primero": ("Alta", 15),
    "Gana local": ("Media-alta", 12),
    "Gana visitante": ("Media-alta", 12),
    "Local gana cualquier mitad": ("Media", 9),
    "Visitante gana cualquier mitad": ("Media", 9),
    "Más de 2.5 goles": ("Media", 8),
    "Ambos anotan - Sí": ("Media", 8),
    "Ambos anotan - No": ("Media", 8),
    "Gol antes del 70": ("Media-baja", 5),
    "Local marca antes del 70": ("Media", 7),
    "Visitante marca antes del 70": ("Media", 7),
    "Más de 1.5 goles": ("Baja", 3),
    "Menos de 4.5 goles": ("Baja", 3),
    "Local marca +0.5": ("Baja", 3),
    "Visitante marca +0.5": ("Baja", 3),
    "1X": ("Baja", 4),
    "X2": ("Baja", 4),
    "12": ("Media", 7),
    "1T +0.5 goles": ("Media", 8),
    "1T -2.5 goles": ("Media-baja", 5),
}


def fragility_for_market(market: str) -> tuple[str, int]:
    return FRAGILITY_RULES.get(market, ("Media", 8))


def decision_score(
    confidence: float,
    probability: float,
    sample: int,
    market: str,
    consistency: str,
) -> float:
    _, penalty = fragility_for_market(market)
    sample_bonus = min(4.0, max(0, sample - 5) * 0.35)
    consistency_bonus = {
        "Muy alta": 4.0,
        "Alta": 2.0,
        "Media": 0.0,
        "Baja": -5.0,
    }.get(consistency, -3.0)

    return round(
        max(
            0.0,
            min(
                100.0,
                confidence
                + probability * 0.07
                + sample_bonus
                + consistency_bonus
                - penalty,
            ),
        ),
        1,
    )


def bet_status(
    confidence: float,
    sample: int,
    risk: str,
    quality: str,
    fragility: str,
    consistency: str,
) -> str:
    if sample < 5 or quality == "Insuficiente":
        return "NO BET"

    if consistency == "Baja":
        return "NO BET"

    if fragility in {"Alta", "Muy alta"}:
        if confidence >= 90 and sample >= 8 and risk != "Alto":
            return "BET CON PRECAUCIÓN"
        return "NO BET"

    if risk == "Alto":
        return "NO BET"

    if confidence >= 87 and sample >= 6:
        return "BET"

    if confidence >= 82 and sample >= 8:
        return "BET CON PRECAUCIÓN"

    return "NO BET"
