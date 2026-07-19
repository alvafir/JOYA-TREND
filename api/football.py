from __future__ import annotations

from typing import Any
import requests
import streamlit as st

from config.settings import API_BASE, CACHE_TTL_SECONDS


def get_api_key() -> str:
    try:
        return str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:
        return ""


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def api_get(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    key = get_api_key()
    if not key:
        raise RuntimeError("Falta APISPORTS_KEY en Streamlit Secrets.")

    response = requests.get(
        f"{API_BASE}/{endpoint.lstrip('/')}",
        headers={"x-apisports-key": key},
        params=params,
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get("errors"):
        raise RuntimeError(f"API-Football devolvió: {payload['errors']}")

    return payload


def response_list(endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    return api_get(endpoint, params).get("response", [])
