from __future__ import annotations

FINISHED = {"FT", "AET", "PEN"}


def is_finished(item):
    return (
        ((item.get("fixture", {}) or {}).get("status", {}) or {}).get("short")
        in FINISHED
    )


def select_venue_fixtures(fixtures, team_id, home, limit):
    selected = []

    for item in fixtures:
        if not is_finished(item):
            continue

        teams = item.get("teams", {}) or {}
        selected_id = (
            (teams.get("home", {}) or {}).get("id")
            if home
            else (teams.get("away", {}) or {}).get("id")
        )

        if selected_id == team_id:
            selected.append(item)

        if len(selected) >= limit:
            break

    return selected


def calculate_basic_metrics(fixtures, team_id):
    percentage_keys = [
        "score",
        "concede",
        "over15",
        "over25",
        "under35",
        "under45",
        "btts",
        "team_over15",
        "first_half_over05",
        "first_half_under25",
        "first_half_btts",
        "win",
        "draw",
        "loss",
    ]

    counters = {key: 0 for key in percentage_keys}
    n = 0
    gf_sum = 0.0
    ga_sum = 0.0
    ht_gf_sum = 0.0
    ht_ga_sum = 0.0
    ht_sample = 0

    for item in fixtures:
        if not is_finished(item):
            continue

        teams = item.get("teams", {}) or {}
        goals = item.get("goals", {}) or {}
        halftime = ((item.get("score", {}) or {}).get("halftime", {}) or {})

        gh = goals.get("home")
        ga = goals.get("away")

        if gh is None or ga is None:
            continue

        home_id = (teams.get("home", {}) or {}).get("id")
        is_home = home_id == team_id
        gf, gc = (gh, ga) if is_home else (ga, gh)

        n += 1
        gf_sum += float(gf)
        ga_sum += float(gc)

        counters["score"] += int(gf >= 1)
        counters["concede"] += int(gc >= 1)
        counters["over15"] += int(gf + gc >= 2)
        counters["over25"] += int(gf + gc >= 3)
        counters["under35"] += int(gf + gc <= 3)
        counters["under45"] += int(gf + gc <= 4)
        counters["btts"] += int(gf >= 1 and gc >= 1)
        counters["team_over15"] += int(gf >= 2)
        counters["win"] += int(gf > gc)
        counters["draw"] += int(gf == gc)
        counters["loss"] += int(gf < gc)

        hth = halftime.get("home")
        hta = halftime.get("away")

        if hth is not None and hta is not None:
            ht_gf, ht_gc = (hth, hta) if is_home else (hta, hth)
            ht_sample += 1
            ht_gf_sum += float(ht_gf)
            ht_ga_sum += float(ht_gc)
            counters["first_half_over05"] += int(hth + hta >= 1)
            counters["first_half_under25"] += int(hth + hta <= 2)
            counters["first_half_btts"] += int(hth >= 1 and hta >= 1)

    if n == 0:
        return {"sample": 0}

    result = {"sample": n}

    for key, value in counters.items():
        denominator = ht_sample if key.startswith("first_half") and ht_sample else n
        result[key] = round(100 * value / denominator, 1)

    result["gf_avg"] = round(gf_sum / n, 2)
    result["ga_avg"] = round(ga_sum / n, 2)
    result["total_goals_avg"] = round((gf_sum + ga_sum) / n, 2)
    result["ht_gf_avg"] = round(ht_gf_sum / ht_sample, 2) if ht_sample else 0.0
    result["ht_ga_avg"] = round(ht_ga_sum / ht_sample, 2) if ht_sample else 0.0

    return result


def event_minute(event):
    event_time = event.get("time", {}) or {}
    elapsed = event_time.get("elapsed")
    extra = event_time.get("extra") or 0

    return None if elapsed is None else int(elapsed) + int(extra)
