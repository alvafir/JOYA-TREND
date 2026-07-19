from __future__ import annotations

API_BASE = "https://v3.football.api-sports.io"
DEFAULT_TIMEZONE = "America/Santiago"
CACHE_TTL_SECONDS = 300
RECENT_MATCHES = 10

# Evita consumir demasiadas solicitudes durante las primeras pruebas.
DEFAULT_SCAN_LIMIT = 20
MAX_SCAN_LIMIT = 50

EXCLUDED_KEYWORDS = {
    "u17",
    "u18",
    "u19",
    "u20",
    "u21",
    "youth",
    "women",
    "femenina",
    "reserve",
    "reserves",
}
