from __future__ import annotations
from datetime import datetime
import json, sqlite3
from pathlib import Path
import pandas as pd
DB_PATH=Path("joya_enterprise_4.db")
def connect():
 c=sqlite3.connect(DB_PATH,timeout=30); c.row_factory=sqlite3.Row; return c
def initialize_data_lake():
 with connect() as c:
  c.execute("CREATE TABLE IF NOT EXISTS analyses(fixture_id INTEGER PRIMARY KEY,summary_json TEXT NOT NULL,markets_json TEXT NOT NULL,updated_at TEXT NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,title TEXT NOT NULL,status TEXT NOT NULL,total INTEGER NOT NULL DEFAULT 0,completed INTEGER NOT NULL DEFAULT 0,failed INTEGER NOT NULL DEFAULT 0,payload_json TEXT NOT NULL,updated_at TEXT NOT NULL)")
  c.execute("CREATE TABLE IF NOT EXISTS job_items(job_id TEXT NOT NULL,position INTEGER NOT NULL,fixture_id INTEGER NOT NULL,fixture_json TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',error TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(job_id,fixture_id))")
  c.commit()
def save_analysis(summary,table):
 initialize_data_lake(); now=datetime.utcnow().isoformat(timespec='seconds'); fid=int(summary['fixture_id'])
 markets=table.to_json(orient='records',force_ascii=False) if table is not None and not table.empty else '[]'
 with connect() as c:
  c.execute("INSERT INTO analyses(fixture_id,summary_json,markets_json,updated_at) VALUES(?,?,?,?) ON CONFLICT(fixture_id) DO UPDATE SET summary_json=excluded.summary_json,markets_json=excluded.markets_json,updated_at=excluded.updated_at",(fid,json.dumps(summary,ensure_ascii=False),markets,now)); c.commit()
def load_all_analyses():
 initialize_data_lake(); summaries=[]; tables={}
 with connect() as c: rows=c.execute("SELECT fixture_id,summary_json,markets_json FROM analyses ORDER BY updated_at DESC").fetchall()
 for r in rows:
  fid=int(r['fixture_id']); summaries.append(json.loads(r['summary_json'])); tables[fid]=pd.DataFrame(json.loads(r['markets_json'] or '[]'))
 ranking=pd.DataFrame(summaries)
 if not ranking.empty and {'Confianza','Muestra'}.issubset(ranking.columns): ranking=ranking.sort_values(['Confianza','Muestra'],ascending=[False,False])
 return ranking,tables
