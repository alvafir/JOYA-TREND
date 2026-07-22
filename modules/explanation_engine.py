from __future__ import annotations


def explain_market(row: dict) -> list[str]:
    """Generate transparent, data-grounded reasons without inventing context."""
    home = float(row.get("Local casa %", 0))
    away = float(row.get("Visitante fuera %", 0))
    probability = float(row.get("Probabilidad %", 0))
    confidence = float(row.get("Confianza JOYA", 0))
    sample = int(row.get("Muestra", 0))
    consistency = str(row.get("Consistencia", ""))
    quality = str(row.get("Calidad", ""))
    risk = str(row.get("Riesgo", ""))

    reasons = [
        f"El local presenta {home:.1f}% de tendencia para este mercado jugando en casa.",
        f"El visitante presenta {away:.1f}% de tendencia para este mercado jugando fuera.",
        f"La combinación estadística del partido es {probability:.1f}%.",
        f"La confianza calibrada JOYA es {confidence:.1f}/100 con una muestra de {sample} partidos.",
    ]

    if consistency:
        reasons.append(f"Consistencia entre ambas tendencias: {consistency}.")
    if quality:
        reasons.append(f"Calidad de datos: {quality}.")
    if risk:
        reasons.append(f"Riesgo estimado: {risk}.")

    return reasons
