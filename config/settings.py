from __future__ import annotations

API_BASE = "https://v3.football.api-sports.io"
DEFAULT_TIMEZONE = "America/Santiago"
CACHE_TTL_SECONDS = 300
RECENT_MATCHES = 10

EXCLUDED_KEYWORDS = {
    "u17", "u18", "u19", "u20", "u21", "u23",
    "youth", "juvenil", "reserve", "reserves",
}

VOLATILE_KEYWORDS = {
    "friendly", "friendlies", "amistoso", "amistosos",
}
