from __future__ import annotations

import math
import statistics
from typing import Any

import pandas as pd

from api import football_api

get_team_fixtures = football_api.get_team_fixtures


def get_fixture_statistics(fixture_id: int):
    """
    Compatibilidad con repositorios que todavía conservan una versión anterior
    de api/football_api.py. Si la función dedicada existe, se usa. Si no,
    se consulta directamente mediante api_list.
    """
    dedicated = getattr(football_api, "get_fixture_statistics", None)

    if callable(dedicated):
        return dedicated(fixture_id)

    return football_api.api_list(
        "fixtures/statistics",
        {"fixture": fixture_id},
    )
from config.settings import RECENT_GENERAL, RECENT_VENUE
from core.probability_engine import (
    calculate_basic_metrics,
    is_finished,
    select_venue_fixtures,
)


STAT_ALIASES = {
    "corners": {"Corner Kicks", "Corners"},
    "yellow_cards": {"Yellow Cards"},
    "red_cards": {"Red Cards"},
    "shots": {"Total Shots"},
    "shots_on_goal": {"Shots on Goal"},
    "fouls": {"Fouls"},
    "offsides": {"Offsides"},
    "saves": {"Goalkeeper Saves"},
    "throw_ins": {"Throw-ins", "Throw Ins", "Throw In"},
    "goal_kicks": {"Goal Kicks", "Goal kicks"},
}

LABELS = {
    "corners": "Córners",
    "yellow_cards": "Tarjetas amarillas",
    "red_cards": "Tarjetas rojas",
    "shots": "Remates totales",
    "shots_on_goal": "Tiros al arco",
    "fouls": "Faltas",
    "offsides": "Offsides",
    "saves": "Atajadas",
    "throw_ins": "Saques de banda",
    "goal_kicks": "Saques de meta",
}


def _numeric(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace("%", "")

    try:
        return float(text)
    except ValueError:
        return None


def _statistics_by_team(fixture_id: int) -> dict[int, dict[str, float]]:
    response = get_fixture_statistics(fixture_id)
    result: dict[int, dict[str, float]] = {}

    for team_block in response:
        team_id = ((team_block.get("team", {}) or {}).get("id"))
        if not team_id:
            continue

        mapped: dict[str, float] = {}

        for stat in team_block.get("statistics", []) or []:
            stat_type = stat.get("type")
            value = _numeric(stat.get("value"))

            if value is None:
                continue

            for key, aliases in STAT_ALIASES.items():
                if stat_type in aliases:
                    mapped[key] = value
                    break

        result[int(team_id)] = mapped

    return result


def _collect_stat_samples(
    fixtures: list[dict],
    team_id: int,
    max_games: int,
) -> dict[str, dict[str, list[float]]]:
    samples = {
        key: {"own": [], "opponent": [], "total": []}
        for key in STAT_ALIASES
    }

    used = 0

    for fixture in fixtures:
        if not is_finished(fixture):
            continue

        fixture_id = ((fixture.get("fixture", {}) or {}).get("id"))
        teams = fixture.get("teams", {}) or {}

        if not fixture_id:
            continue

        stats = _statistics_by_team(int(fixture_id))

        if team_id not in stats or len(stats) < 2:
            continue

        opponent_ids = [key for key in stats if key != team_id]

        if not opponent_ids:
            continue

        opponent_id = opponent_ids[0]
        own_stats = stats.get(team_id, {})
        opponent_stats = stats.get(opponent_id, {})

        for key in STAT_ALIASES:
            own = own_stats.get(key)
            opponent = opponent_stats.get(key)

            if own is not None:
                samples[key]["own"].append(float(own))

            if opponent is not None:
                samples[key]["opponent"].append(float(opponent))

            if own is not None and opponent is not None:
                samples[key]["total"].append(float(own + opponent))

        used += 1

        if used >= max_games:
            break

    samples["_meta"] = {"games": used}
    return samples


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def _std(values: list[float]) -> float:
    if len(values) >= 2:
        return max(0.75, statistics.pstdev(values))
    return 1.5


def _poisson_probability(lam: float, goals: int) -> float:
    return math.exp(-lam) * (lam ** goals) / math.factorial(goals)


def _goal_distribution(expected_total: float, max_goals: int = 9) -> dict[int, float]:
    distribution = {
        goals: _poisson_probability(expected_total, goals)
        for goals in range(max_goals + 1)
    }

    remainder = max(0.0, 1.0 - sum(distribution.values()))
    distribution[max_goals] += remainder
    return distribution


def _range_probability(
    distribution: dict[int, float],
    minimum: int,
    maximum: int,
) -> float:
    return round(
        100 * sum(
            probability
            for goals, probability in distribution.items()
            if minimum <= goals <= maximum
        ),
        1,
    )


def _projection_status(probability: float, sample: int) -> str:
    if sample < 4:
        return "NO BET"
    if probability >= 78:
        return "BET"
    if probability >= 68:
        return "BET CON PRECAUCIÓN"
    return "NO BET"


def _confidence(probability: float, sample: int) -> float:
    sample_factor = min(1.0, sample / 8)
    return round(
        max(
            0.0,
            min(
                99.0,
                65 + (probability - 65) * (0.62 + 0.22 * sample_factor),
            ),
        ),
        1,
    )


def _projected_range(expected: float, spread: float) -> str:
    low = max(0, int(math.floor(expected - spread)))
    high = max(low, int(math.ceil(expected + spread)))
    return f"{low}–{high}"


def _line_probability(values: list[float], line: float, over: bool = True) -> float:
    if not values:
        return 0.0

    hits = sum(
        value > line if over else value < line
        for value in values
    )

    return round(100 * hits / len(values), 1)


def _suggested_line(projected: float, category: str) -> float:
    buffers = {
        "corners": 1.25,
        "yellow_cards": 1.0,
        "shots": 3.0,
        "shots_on_goal": 1.5,
        "fouls": 3.0,
        "offsides": 1.0,
        "saves": 1.0,
        "throw_ins": 4.0,
        "goal_kicks": 2.0,
    }

    buffer = buffers.get(category, 1.0)
    base = max(0.5, projected - buffer)
    return math.floor(base) + 0.5


def build_goal_projection(fixture: dict) -> dict:
    teams = fixture.get("teams", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    home_id = home.get("id")
    away_id = away.get("id")

    if not home_id or not away_id:
        return {}

    home_all = get_team_fixtures(int(home_id))
    away_all = get_team_fixtures(int(away_id))

    home_base = (
        select_venue_fixtures(
            home_all,
            int(home_id),
            True,
            RECENT_VENUE,
        )
        or home_all[:RECENT_GENERAL]
    )

    away_base = (
        select_venue_fixtures(
            away_all,
            int(away_id),
            False,
            RECENT_VENUE,
        )
        or away_all[:RECENT_GENERAL]
    )

    hm = calculate_basic_metrics(home_base, int(home_id))
    am = calculate_basic_metrics(away_base, int(away_id))

    sample = min(
        int(hm.get("sample", 0)),
        int(am.get("sample", 0)),
    )

    home_expected = round(
        max(
            0.15,
            min(
                3.5,
                (
                    float(hm.get("gf_avg", 0))
                    + float(am.get("ga_avg", 0))
                )
                / 2,
            ),
        ),
        2,
    )

    away_expected = round(
        max(
            0.15,
            min(
                3.5,
                (
                    float(am.get("gf_avg", 0))
                    + float(hm.get("ga_avg", 0))
                )
                / 2,
            ),
        ),
        2,
    )

    total_expected = round(home_expected + away_expected, 2)
    distribution = _goal_distribution(total_expected)

    ranges = [
        (0, 2),
        (0, 3),
        (0, 4),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (2, 4),
        (2, 5),
        (2, 6),
        (3, 4),
        (3, 5),
        (3, 6),
        (5, 6),
    ]

    range_rows = []

    for minimum, maximum in ranges:
        probability = _range_probability(
            distribution,
            minimum,
            maximum,
        )

        range_rows.append({
            "Rango": f"{minimum}–{maximum}",
            "Probabilidad %": probability,
            "Confianza JOYA": _confidence(probability, sample),
            "Muestra": sample,
            "Estado": _projection_status(probability, sample),
        })

    score_rows = []

    for home_goals in range(5):
        for away_goals in range(5):
            probability = (
                _poisson_probability(home_expected, home_goals)
                * _poisson_probability(away_expected, away_goals)
            )

            score_rows.append({
                "Marcador": f"{home_goals}-{away_goals}",
                "Probabilidad %": round(100 * probability, 1),
            })

    score_rows = sorted(
        score_rows,
        key=lambda row: row["Probabilidad %"],
        reverse=True,
    )[:6]

    return {
        "home_team": home.get("name") or "Local",
        "away_team": away.get("name") or "Visitante",
        "home_expected": home_expected,
        "away_expected": away_expected,
        "total_expected": total_expected,
        "total_range": _projected_range(total_expected, 1.25),
        "home_range": _projected_range(home_expected, 0.85),
        "away_range": _projected_range(away_expected, 0.85),
        "sample": sample,
        "ranges": pd.DataFrame(range_rows).sort_values(
            ["Confianza JOYA", "Probabilidad %"],
            ascending=[False, False],
        ),
        "scores": pd.DataFrame(score_rows),
    }


def build_advanced_projection(
    fixture: dict,
    stat_sample: int = 3,
) -> dict:
    teams = fixture.get("teams", {}) or {}
    fixture_info = fixture.get("fixture", {}) or {}
    home = teams.get("home", {}) or {}
    away = teams.get("away", {}) or {}

    home_id = home.get("id")
    away_id = away.get("id")

    if not home_id or not away_id:
        return {"rows": pd.DataFrame()}

    home_all = get_team_fixtures(int(home_id))
    away_all = get_team_fixtures(int(away_id))

    home_base = (
        select_venue_fixtures(
            home_all,
            int(home_id),
            True,
            RECENT_VENUE,
        )
        or home_all[:RECENT_GENERAL]
    )

    away_base = (
        select_venue_fixtures(
            away_all,
            int(away_id),
            False,
            RECENT_VENUE,
        )
        or away_all[:RECENT_GENERAL]
    )

    home_samples = _collect_stat_samples(
        home_base,
        int(home_id),
        stat_sample,
    )

    away_samples = _collect_stat_samples(
        away_base,
        int(away_id),
        stat_sample,
    )

    rows = []
    referee = fixture_info.get("referee") or "Sin información"

    for key, label in LABELS.items():
        home_own = _mean(home_samples[key]["own"])
        away_own = _mean(away_samples[key]["own"])
        home_opponent = _mean(home_samples[key]["opponent"])
        away_opponent = _mean(away_samples[key]["opponent"])

        home_projected = (
            round((home_own + away_opponent) / 2, 2)
            if home_own is not None and away_opponent is not None
            else None
        )

        away_projected = (
            round((away_own + home_opponent) / 2, 2)
            if away_own is not None and home_opponent is not None
            else None
        )

        total_projected = (
            round(home_projected + away_projected, 2)
            if home_projected is not None and away_projected is not None
            else None
        )

        combined_totals = (
            home_samples[key]["total"]
            + away_samples[key]["total"]
        )

        sample = len(combined_totals)

        if total_projected is None or sample < 2:
            rows.append({
                "Categoría": label,
                "Proyección total": None,
                "Rango": "Sin datos",
                "Local proyectado": home_projected,
                "Visitante proyectado": away_projected,
                "Línea sugerida": "No disponible",
                "Probabilidad %": None,
                "Confianza JOYA": None,
                "Muestra": sample,
                "Estado": "NO BET",
                "Motivo": "Cobertura insuficiente de API-Football",
            })
            continue

        spread = _std(combined_totals)
        line = _suggested_line(total_projected, key)
        probability = _line_probability(
            combined_totals,
            line,
            over=True,
        )

        rows.append({
            "Categoría": label,
            "Proyección total": round(total_projected, 1),
            "Rango": _projected_range(
                total_projected,
                max(1.0, spread),
            ),
            "Local proyectado": (
                round(home_projected, 1)
                if home_projected is not None
                else None
            ),
            "Visitante proyectado": (
                round(away_projected, 1)
                if away_projected is not None
                else None
            ),
            "Línea sugerida": f"Más de {line}",
            "Probabilidad %": probability,
            "Confianza JOYA": _confidence(probability, sample),
            "Muestra": sample,
            "Estado": _projection_status(probability, sample),
            "Motivo": (
                "Proyección basada en rendimiento local/visitante reciente"
            ),
        })

    return {
        "rows": pd.DataFrame(rows),
        "referee": referee,
        "referee_note": (
            "El árbitro se muestra como contexto. Esta versión no inventa "
            "un ajuste tarjetero cuando no existe historial arbitral suficiente."
        ),
        "home_games": int(home_samples["_meta"]["games"]),
        "away_games": int(away_samples["_meta"]["games"]),
    }
