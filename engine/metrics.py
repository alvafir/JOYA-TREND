from __future__ import annotations
from typing import Any

FINISHED_STATUSES = {"FT", "AET", "PEN"}


def team_metrics(fixtures: list[dict[str, Any]], team_id: int) -> dict[str, float]:
    total = wins = draws = losses = 0
    scored = conceded = over15 = btts = under45 = 0
    goals_for = goals_against = 0

    for item in fixtures:
        fixture = item.get("fixture", {}) or {}
        if (fixture.get("status", {}) or {}).get("short") not in FINISHED_STATUSES:
            continue

        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        home = teams.get("home", {}) or {}
        away = teams.get("away", {}) or {}

        gh, ga = goals.get("home"), goals.get("away")
        if gh is None or ga is None:
            continue

        is_home = home.get("id") == team_id
        gf, gc = (gh, ga) if is_home else (ga, gh)

        total += 1
        goals_for += gf
        goals_against += gc
        scored += int(gf >= 1)
        conceded += int(gc >= 1)
        over15 += int(gf + gc >= 2)
        btts += int(gf >= 1 and gc >= 1)
        under45 += int(gf + gc <= 4)

        if gf > gc:
            wins += 1
        elif gf == gc:
            draws += 1
        else:
            losses += 1

    if total == 0:
        return {"sample": 0}

    pct = lambda value: round(value * 100 / total, 1)
    return {
        "sample": total,
        "win_pct": pct(wins),
        "draw_pct": pct(draws),
        "loss_pct": pct(losses),
        "score_pct": pct(scored),
        "concede_pct": pct(conceded),
        "over15_pct": pct(over15),
        "btts_pct": pct(btts),
        "under45_pct": pct(under45),
        "gf_avg": round(goals_for / total, 2),
        "ga_avg": round(goals_against / total, 2),
    }
