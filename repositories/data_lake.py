from __future__ import annotations
from datetime import datetime
import json
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path("joya_enterprise_4.db")

def connect():
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    return connection

def initialize_data_lake():
    with connect() as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS analyses(fixture_id INTEGER PRIMARY KEY,summary_json TEXT NOT NULL,markets_json TEXT NOT NULL,updated_at TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,title TEXT NOT NULL,status TEXT NOT NULL,total INTEGER NOT NULL DEFAULT 0,completed INTEGER NOT NULL DEFAULT 0,failed INTEGER NOT NULL DEFAULT 0,payload_json TEXT NOT NULL,updated_at TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS job_items(job_id TEXT NOT NULL,position INTEGER NOT NULL,fixture_id INTEGER NOT NULL,fixture_json TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',error TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(job_id,fixture_id))")
        connection.commit()

def save_analysis(summary, table):
    initialize_data_lake()
    now = datetime.utcnow().isoformat(timespec="seconds")
    fixture_id = int(summary["fixture_id"])
    markets = table.to_json(orient="records", force_ascii=False) if table is not None and not table.empty else "[]"
    with connect() as connection:
        connection.execute(
            "INSERT INTO analyses(fixture_id,summary_json,markets_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET summary_json=excluded.summary_json,markets_json=excluded.markets_json,updated_at=excluded.updated_at",
            (fixture_id, json.dumps(summary, ensure_ascii=False), markets, now),
        )
        connection.commit()

def load_all_analyses():
    initialize_data_lake()
    summaries = []
    tables = {}
    required = {"fixture_id", "Confianza", "Muestra"}
    with connect() as connection:
        rows = connection.execute("SELECT fixture_id,summary_json,markets_json FROM analyses ORDER BY updated_at DESC").fetchall()
    for row in rows:
        fixture_id = int(row["fixture_id"])
        try:
            summary = json.loads(row["summary_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not isinstance(summary, dict) or not required.issubset(summary.keys()):
            continue
        summaries.append(summary)
        try:
            markets = json.loads(row["markets_json"] or "[]")
        except (TypeError, json.JSONDecodeError):
            markets = []
        tables[fixture_id] = pd.DataFrame(markets)
    ranking = pd.DataFrame(summaries)
    if not ranking.empty:
        ranking = ranking.sort_values(["Confianza", "Muestra"], ascending=[False, False])
    return ranking, tables

def clear_incompatible_analyses():
    initialize_data_lake()
    required = {"fixture_id", "Confianza", "Muestra"}
    invalid_ids = []
    with connect() as connection:
        rows = connection.execute("SELECT fixture_id,summary_json FROM analyses").fetchall()
        for row in rows:
            try:
                summary = json.loads(row["summary_json"])
            except (TypeError, json.JSONDecodeError):
                invalid_ids.append(int(row["fixture_id"]))
                continue
            if not isinstance(summary, dict) or not required.issubset(summary.keys()):
                invalid_ids.append(int(row["fixture_id"]))
        for fixture_id in invalid_ids:
            connection.execute("DELETE FROM analyses WHERE fixture_id = ?", (fixture_id,))
        connection.commit()
    return len(invalid_ids)
