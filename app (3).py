from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests
import streamlit as st


st.set_page_config(
    page_title="JOYA TREND PICKS",
    page_icon="💎",
    layout="wide",
)

st.title("💎 JOYA TREND PICKS")
st.caption(
    "Cartelera automática + análisis estadístico básico con "
    "TheSportsDB y football-data.org"
)


# ============================================================
# CONFIGURACIÓN Y SOLICITUDES
# ============================================================

def get_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
        return str(value).strip()
    except Exception:
        return default


@st.cache_data(ttl=300, show_spinner=False)
def request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=20,
        )

        try:
            payload: Any = response.json()
        except ValueError:
            payload = {"raw_response": response.text[:1000]}

        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "payload": payload,
            "requested_url": response.url,
            "error": "" if response.ok else f"HTTP {response.status_code}",
        }

    except requests.RequestException as exc:
        return {
            "ok": False,
            "status_code": None,
            "payload": {},
            "requested_url": url,
            "error": str(exc),
        }


# ============================================================
# CARTELERA
# ============================================================

def get_thesportsdb_matches(target_date: str, api_key: str) -> dict[str, Any]:
    key = api_key or "123"
    url = f"https://www.thesportsdb.com/api/v1/json/{key}/eventsday.php"

    result = request_json(
        url,
        params={"d": target_date, "s": "Soccer"},
    )

    events: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_events = result["payload"].get("events")
        if isinstance(raw_events, list):
            events = raw_events

    result["events"] = events
    return result


def get_football_data_matches(
    target_date: str,
    api_key: str,
) -> dict[str, Any]:
    if not api_key:
        return {
            "ok": False,
            "status_code": None,
            "payload": {},
            "error": "Falta FOOTBALL_DATA_API_KEY.",
            "matches": [],
        }

    result = request_json(
        "https://api.football-data.org/v4/matches",
        headers={"X-Auth-Token": api_key},
        params={
            "dateFrom": target_date,
            "dateTo": target_date,
        },
    )

    matches: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_matches = result["payload"].get("matches")
        if isinstance(raw_matches, list):
            matches = raw_matches

    result["matches"] = matches
    return result


def parse_thesportsdb(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for event in events:
        home = str(event.get("strHomeTeam") or "").strip()
        away = str(event.get("strAwayTeam") or "").strip()

        if not home or not away:
            continue

        rows.append(
            {
                "Fuente": "TheSportsDB",
                "Competición": str(event.get("strLeague") or ""),
                "Local": home,
                "Visitante": away,
                "Fecha": str(event.get("dateEvent") or ""),
                "Hora": str(event.get("strTime") or ""),
                "Estado": str(event.get("strStatus") or "PROGRAMADO"),
                "id_partido": str(event.get("idEvent") or ""),
                "id_local": str(event.get("idHomeTeam") or ""),
                "id_visitante": str(event.get("idAwayTeam") or ""),
            }
        )

    return rows


def parse_football_data(
    matches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for match in matches:
        competition = match.get("competition") or {}
        home_team = match.get("homeTeam") or {}
        away_team = match.get("awayTeam") or {}
        utc_date = str(match.get("utcDate") or "")

        home = str(home_team.get("name") or "").strip()
        away = str(away_team.get("name") or "").strip()

        if not home or not away:
            continue

        rows.append(
            {
                "Fuente": "football-data.org",
                "Competición": str(competition.get("name") or ""),
                "Local": home,
                "Visitante": away,
                "Fecha": utc_date[:10],
                "Hora": utc_date[11:16] if len(utc_date) >= 16 else "",
                "Estado": str(match.get("status") or ""),
                "id_partido": str(match.get("id") or ""),
                "id_local": str(home_team.get("id") or ""),
                "id_visitante": str(away_team.get("id") or ""),
            }
        )

    return rows


def normalize_text(value: Any) -> str:
    return " ".join(str(value or "").lower().strip().split())


def deduplicate_matches(rows: list[dict[str, Any]]) -> pd.DataFrame:
    visible_columns = [
        "Fuente",
        "Competición",
        "Local",
        "Visitante",
        "Fecha",
        "Hora",
        "Estado",
        "id_partido",
        "id_local",
        "id_visitante",
    ]

    if not rows:
        return pd.DataFrame(columns=visible_columns)

    df = pd.DataFrame(rows)

    df["_key"] = (
        df["Fecha"].map(normalize_text)
        + "|"
        + df["Local"].map(normalize_text)
        + "|"
        + df["Visitante"].map(normalize_text)
    )

    df = df.drop_duplicates(subset="_key", keep="first")
    return df.drop(columns="_key").reset_index(drop=True)


# ============================================================
# HISTORIAL DE EQUIPOS
# ============================================================

def get_football_data_team_history(
    team_id: str,
    api_key: str,
    before_date: str,
    limit: int = 10,
) -> dict[str, Any]:
    if not team_id or not api_key:
        return {"ok": False, "matches": [], "error": "ID o token no disponible."}

    date_to = (
        date.fromisoformat(before_date) - timedelta(days=1)
    ).isoformat()
    date_from = (
        date.fromisoformat(before_date) - timedelta(days=400)
    ).isoformat()

    result = request_json(
        f"https://api.football-data.org/v4/teams/{team_id}/matches",
        headers={"X-Auth-Token": api_key},
        params={
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": "FINISHED",
            "limit": min(max(limit, 1), 50),
        },
    )

    matches: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_matches = result["payload"].get("matches")
        if isinstance(raw_matches, list):
            matches = raw_matches[-limit:]

    return {
        "ok": result["ok"],
        "matches": matches,
        "error": result.get("error", ""),
        "status_code": result.get("status_code"),
    }


def get_thesportsdb_team_history(
    team_id: str,
    api_key: str,
) -> dict[str, Any]:
    if not team_id:
        return {"ok": False, "matches": [], "error": "ID del equipo no disponible."}

    key = api_key or "123"
    result = request_json(
        f"https://www.thesportsdb.com/api/v1/json/{key}/eventslast.php",
        params={"id": team_id},
    )

    matches: list[dict[str, Any]] = []
    if result["ok"] and isinstance(result["payload"], dict):
        raw_results = result["payload"].get("results")
        if isinstance(raw_results, list):
            matches = raw_results

    return {
        "ok": result["ok"],
        "matches": matches,
        "error": result.get("error", ""),
        "status_code": result.get("status_code"),
    }


def parse_score(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def normalize_history_football_data(
    matches: list[dict[str, Any]],
    team_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for match in matches:
        home = match.get("homeTeam") or {}
        away = match.get("awayTeam") or {}
        score = match.get("score") or {}
        full_time = score.get("fullTime") or {}

        home_goals = parse_score(full_time.get("home"))
        away_goals = parse_score(full_time.get("away"))

        if home_goals is None or away_goals is None:
            continue

        is_home = str(home.get("id") or "") == str(team_id)
        goals_for = home_goals if is_home else away_goals
        goals_against = away_goals if is_home else home_goals

        rows.append(
            {
                "Fecha": str(match.get("utcDate") or "")[:10],
                "Rival": str((away if is_home else home).get("name") or ""),
                "GF": goals_for,
                "GC": goals_against,
                "Total": home_goals + away_goals,
                "BTTS": home_goals > 0 and away_goals > 0,
                "Resultado": (
                    "G"
                    if goals_for > goals_against
                    else "E"
                    if goals_for == goals_against
                    else "P"
                ),
            }
        )

    return rows


def normalize_history_thesportsdb(
    matches: list[dict[str, Any]],
    team_id: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for match in matches:
        home_id = str(match.get("idHomeTeam") or "")
        home_goals = parse_score(match.get("intHomeScore"))
        away_goals = parse_score(match.get("intAwayScore"))

        if home_goals is None or away_goals is None:
            continue

        is_home = home_id == str(team_id)
        goals_for = home_goals if is_home else away_goals
        goals_against = away_goals if is_home else home_goals

        rows.append(
            {
                "Fecha": str(match.get("dateEvent") or ""),
                "Rival": str(
                    match.get("strAwayTeam")
                    if is_home
                    else match.get("strHomeTeam")
                    or ""
                ),
                "GF": goals_for,
                "GC": goals_against,
                "Total": home_goals + away_goals,
                "BTTS": home_goals > 0 and away_goals > 0,
                "Resultado": (
                    "G"
                    if goals_for > goals_against
                    else "E"
                    if goals_for == goals_against
                    else "P"
                ),
            }
        )

    return rows


# ============================================================
# MOTOR DE PICKS
# ============================================================

def team_metrics(history: list[dict[str, Any]]) -> dict[str, float]:
    if not history:
        return {
            "partidos": 0,
            "gf": 0.0,
            "gc": 0.0,
            "over15": 0.0,
            "under45": 0.0,
            "btts": 0.0,
            "marca": 0.0,
            "invicto": 0.0,
        }

    n = len(history)

    return {
        "partidos": float(n),
        "gf": sum(item["GF"] for item in history) / n,
        "gc": sum(item["GC"] for item in history) / n,
        "over15": 100 * sum(item["Total"] >= 2 for item in history) / n,
        "under45": 100 * sum(item["Total"] <= 4 for item in history) / n,
        "btts": 100 * sum(bool(item["BTTS"]) for item in history) / n,
        "marca": 100 * sum(item["GF"] >= 1 for item in history) / n,
        "invicto": 100 * sum(item["Resultado"] in {"G", "E"} for item in history) / n,
    }


def blended_probability(home_value: float, away_value: float) -> float:
    return round((home_value + away_value) / 2, 1)


def confidence_tier(probability: float, sample_size: int) -> str:
    if sample_size < 6:
        return "NO BET"
    if probability >= 88 and sample_size >= 16:
        return "S++"
    if probability >= 82 and sample_size >= 12:
        return "S+"
    if probability >= 76 and sample_size >= 8:
        return "A++"
    return "NO BET"


def build_picks(
    home_metrics: dict[str, float],
    away_metrics: dict[str, float],
) -> list[dict[str, Any]]:
    sample_size = int(home_metrics["partidos"] + away_metrics["partidos"])

    candidates = [
        {
            "Mercado": "Más de 1.5 goles",
            "Probabilidad": blended_probability(
                home_metrics["over15"],
                away_metrics["over15"],
            ),
        },
        {
            "Mercado": "Menos de 4.5 goles",
            "Probabilidad": blended_probability(
                home_metrics["under45"],
                away_metrics["under45"],
            ),
        },
        {
            "Mercado": "Ambos equipos anotan",
            "Probabilidad": blended_probability(
                home_metrics["btts"],
                away_metrics["btts"],
            ),
        },
        {
            "Mercado": "Local marca +0.5 gol",
            "Probabilidad": round(
                (
                    home_metrics["marca"]
                    + min(100.0, away_metrics["gc"] * 55)
                )
                / 2,
                1,
            ),
        },
        {
            "Mercado": "Visitante marca +0.5 gol",
            "Probabilidad": round(
                (
                    away_metrics["marca"]
                    + min(100.0, home_metrics["gc"] * 55)
                )
                / 2,
                1,
            ),
        },
        {
            "Mercado": "Local o empate",
            "Probabilidad": round(
                (
                    home_metrics["invicto"]
                    + (100 - away_metrics["invicto"] / 2)
                )
                / 2,
                1,
            ),
        },
        {
            "Mercado": "Visitante o empate",
            "Probabilidad": round(
                (
                    away_metrics["invicto"]
                    + (100 - home_metrics["invicto"] / 2)
                )
                / 2,
                1,
            ),
        },
    ]

    for candidate in candidates:
        candidate["Tier"] = confidence_tier(
            candidate["Probabilidad"],
            sample_size,
        )
        candidate["Muestra"] = sample_size

    return sorted(
        candidates,
        key=lambda item: item["Probabilidad"],
        reverse=True,
    )


# ============================================================
# INTERFAZ
# ============================================================

football_data_key = get_secret("FOOTBALL_DATA_API_KEY")
thesportsdb_key = get_secret("THESPORTSDB_API_KEY", "123")

if "selected_date" not in st.session_state:
    st.session_state.selected_date = date.today()

if "range_days" not in st.session_state:
    st.session_state.range_days = 1


button_columns = st.columns(4)

with button_columns[0]:
    if st.button("📅 HOY", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 1

with button_columns[1]:
    if st.button("📅 MAÑANA", use_container_width=True):
        st.session_state.selected_date = date.today() + timedelta(days=1)
        st.session_state.range_days = 1

with button_columns[2]:
    if st.button("📆 PRÓXIMOS 3 DÍAS", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 3

with button_columns[3]:
    if st.button("🗓 PRÓXIMOS 7 DÍAS", use_container_width=True):
        st.session_state.selected_date = date.today()
        st.session_state.range_days = 7


control_columns = st.columns(2)

with control_columns[0]:
    selected_date = st.date_input(
        "Elegir fecha inicial",
        value=st.session_state.selected_date,
    )
    st.session_state.selected_date = selected_date

with control_columns[1]:
    range_days = st.selectbox(
        "Cantidad de días",
        options=[1, 3, 7],
        index=[1, 3, 7].index(st.session_state.range_days),
    )
    st.session_state.range_days = range_days


all_rows: list[dict[str, Any]] = []
diagnostics: list[dict[str, Any]] = []

with st.spinner("Buscando partidos..."):
    for offset in range(st.session_state.range_days):
        current_date = st.session_state.selected_date + timedelta(days=offset)
        target_date = current_date.isoformat()

        sportsdb_result = get_thesportsdb_matches(
            target_date,
            thesportsdb_key,
        )
        football_result = get_football_data_matches(
            target_date,
            football_data_key,
        )

        sportsdb_rows = parse_thesportsdb(
            sportsdb_result.get("events", [])
        )
        football_rows = parse_football_data(
            football_result.get("matches", [])
        )

        all_rows.extend(sportsdb_rows)
        all_rows.extend(football_rows)

        diagnostics.append(
            {
                "Fecha": target_date,
                "TheSportsDB": (
                    "Conectada" if sportsdb_result["ok"] else "Error"
                ),
                "Partidos TheSportsDB": len(sportsdb_rows),
                "football-data": (
                    "Conectada" if football_result["ok"] else "Error"
                ),
                "Partidos football-data": len(football_rows),
            }
        )


matches_df = deduplicate_matches(all_rows)

start_label = st.session_state.selected_date.isoformat()
end_label = (
    st.session_state.selected_date
    + timedelta(days=st.session_state.range_days - 1)
).isoformat()

if st.session_state.range_days == 1:
    st.subheader(f"⚽ Partidos del {start_label}")
else:
    st.subheader(f"⚽ Partidos del {start_label} al {end_label}")

if matches_df.empty:
    st.warning(
        "No se encontraron partidos para la fecha o rango seleccionado."
    )
else:
    st.success(f"Se encontraron {len(matches_df)} partidos sin duplicados.")

    display_df = matches_df[
        [
            "Fuente",
            "Competición",
            "Local",
            "Visitante",
            "Fecha",
            "Hora",
            "Estado",
        ]
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.header("🩸 Analizador de picks")

    match_options: dict[str, int] = {}
    for index, row in matches_df.iterrows():
        label = (
            f"{row['Fecha']} | {row['Local']} vs {row['Visitante']} "
            f"| {row['Competición']} | {row['Fuente']}"
        )
        match_options[label] = index

    selected_label = st.selectbox(
        "Selecciona un partido",
        options=list(match_options.keys()),
    )

    selected_match = matches_df.loc[match_options[selected_label]]

    st.write(
        f"**{selected_match['Local']} vs "
        f"{selected_match['Visitante']}**"
    )

    if st.button(
        "🔎 ANALIZAR PARTIDO",
        type="primary",
        use_container_width=True,
    ):
        with st.spinner("Consultando historial y calculando mercados..."):
            source = selected_match["Fuente"]
            match_date = selected_match["Fecha"]

            if source == "football-data.org":
                home_result = get_football_data_team_history(
                    selected_match["id_local"],
                    football_data_key,
                    match_date,
                    limit=10,
                )
                away_result = get_football_data_team_history(
                    selected_match["id_visitante"],
                    football_data_key,
                    match_date,
                    limit=10,
                )

                home_history = normalize_history_football_data(
                    home_result["matches"],
                    selected_match["id_local"],
                )
                away_history = normalize_history_football_data(
                    away_result["matches"],
                    selected_match["id_visitante"],
                )

            else:
                home_result = get_thesportsdb_team_history(
                    selected_match["id_local"],
                    thesportsdb_key,
                )
                away_result = get_thesportsdb_team_history(
                    selected_match["id_visitante"],
                    thesportsdb_key,
                )

                home_history = normalize_history_thesportsdb(
                    home_result["matches"],
                    selected_match["id_local"],
                )
                away_history = normalize_history_thesportsdb(
                    away_result["matches"],
                    selected_match["id_visitante"],
                )

            home_metrics = team_metrics(home_history)
            away_metrics = team_metrics(away_history)
            picks = build_picks(home_metrics, away_metrics)

        metric_columns = st.columns(4)
        metric_columns[0].metric(
            "Partidos local",
            int(home_metrics["partidos"]),
        )
        metric_columns[1].metric(
            "Partidos visitante",
            int(away_metrics["partidos"]),
        )
        metric_columns[2].metric(
            "Promedio GF local",
            f"{home_metrics['gf']:.2f}",
        )
        metric_columns[3].metric(
            "Promedio GF visitante",
            f"{away_metrics['gf']:.2f}",
        )

        total_sample = int(
            home_metrics["partidos"] + away_metrics["partidos"]
        )

        if total_sample < 6:
            st.error(
                "NO BET: la API gratuita entregó muy pocos antecedentes "
                "para generar una recomendación responsable."
            )
        else:
            valid_picks = [
                pick for pick in picks if pick["Tier"] != "NO BET"
            ]

            if valid_picks:
                best_pick = valid_picks[0]
                st.success(
                    f"🎯 PICK PRINCIPAL: {best_pick['Mercado']} | "
                    f"{best_pick['Probabilidad']}% | {best_pick['Tier']}"
                )
            else:
                st.warning(
                    "NO BET: ningún mercado supera los filtros mínimos."
                )

        picks_df = pd.DataFrame(picks)
        st.dataframe(
            picks_df[
                ["Mercado", "Probabilidad", "Tier", "Muestra"]
            ],
            use_container_width=True,
            hide_index=True,
        )

        history_columns = st.columns(2)

        with history_columns[0]:
            st.subheader(
                f"Últimos resultados: {selected_match['Local']}"
            )
            if home_history:
                st.dataframe(
                    pd.DataFrame(home_history),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Sin historial disponible.")

        with history_columns[1]:
            st.subheader(
                f"Últimos resultados: {selected_match['Visitante']}"
            )
            if away_history:
                st.dataframe(
                    pd.DataFrame(away_history),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Sin historial disponible.")

        st.caption(
            "Las probabilidades son estimaciones descriptivas basadas en "
            "resultados recientes disponibles. No son garantías ni sustituyen "
            "un análisis completo de alineaciones, lesiones, cuotas y contexto."
        )


with st.expander("🧪 Diagnóstico de APIs"):
    st.dataframe(
        pd.DataFrame(diagnostics),
        use_container_width=True,
        hide_index=True,
    )

    st.info(
        "TheSportsDB gratuito puede entregar muy pocos partidos anteriores "
        "por equipo. En esos casos la app mostrará NO BET en lugar de inventar "
        "una recomendación."
    )
