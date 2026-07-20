from typing import Any
import requests, streamlit as st
from config.settings import API_BASE
def get_api_key():
    try:return str(st.secrets["APISPORTS_KEY"]).strip()
    except Exception:return ""
@st.cache_data(ttl=300,show_spinner=False)
def api_get(endpoint:str,params:dict[str,Any]):
    key=get_api_key()
    if not key: raise RuntimeError("Falta APISPORTS_KEY en Streamlit Secrets.")
    r=requests.get(f"{API_BASE}/{endpoint.lstrip('/')}",headers={"x-apisports-key":key},params=params,timeout=30)
    r.raise_for_status(); p=r.json()
    if p.get("errors"): raise RuntimeError(str(p["errors"]))
    return p
def api_list(endpoint,params): return api_get(endpoint,params).get("response",[])
def test_connection():
    try:
        p=api_get("status",{}); a=(p.get("response") or {}).get("account",{}) or {}
        return True,str(a.get("firstname") or "Cuenta activa")
    except Exception as e:return False,str(e)
@st.cache_data(ttl=1800,show_spinner=False)
def get_team_fixtures(team_id:int,last:int=25): return api_list("fixtures",{"team":team_id,"last":last})
@st.cache_data(ttl=3600,show_spinner=False)
def get_fixture_events(fixture_id:int): return api_list("fixtures/events",{"fixture":fixture_id})
