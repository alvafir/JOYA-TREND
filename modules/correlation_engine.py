from __future__ import annotations


def market_family(group: str, market: str) -> str:
    text = f"{group} {market}".lower()

    if "minuto" in text or "antes del 70" in text or "antes del 10" in text:
        return "timing_goals"
    if "primer gol" in text or "marca primero" in text:
        return "first_goal"
    if "btts" in text or "ambos anotan" in text:
        return "btts"
    if "local marca" in text or "visitante marca" in text or "goles por equipo" in text:
        return "team_goals"
    if "goles" in text or "primer tiempo" in text:
        return "match_goals"
    if "doble oportunidad" in text or market in {"1X", "X2", "12"}:
        return "result_protection"
    return group.lower().strip()


def correlation_level(a: dict, b: dict) -> str:
    if int(a["fixture_id"]) == int(b["fixture_id"]):
        return "Muy alta"

    family_a = market_family(str(a.get("Grupo", "")), str(a.get("Mercado", "")))
    family_b = market_family(str(b.get("Grupo", "")), str(b.get("Mercado", "")))

    if family_a == family_b:
        return "Alta"

    goal_families = {"timing_goals", "first_goal", "btts", "team_goals", "match_goals"}
    if family_a in goal_families and family_b in goal_families:
        return "Media"

    return "Baja"


def cart_correlation(rows: list[dict]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    worst = "Baja"
    rank = {"Baja": 0, "Media": 1, "Alta": 2, "Muy alta": 3}

    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            level = correlation_level(rows[i], rows[j])
            if rank[level] > rank[worst]:
                worst = level
            if level in {"Alta", "Muy alta"}:
                warnings.append(
                    f"{rows[i]['Partido']} · {rows[i]['Mercado']} ↔ "
                    f"{rows[j]['Partido']} · {rows[j]['Mercado']}: correlación {level.lower()}."
                )

    return worst, warnings
