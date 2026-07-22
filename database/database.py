import sqlite3
from pathlib import Path
DB=Path("joya_x.db")
def get_connection():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def initialize_database():
    with get_connection() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS analyses(id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT DEFAULT CURRENT_TIMESTAMP,fixture_id INTEGER,country TEXT,league TEXT,home_team TEXT,away_team TEXT,market_group TEXT,market TEXT,probability REAL,confidence REAL,tier TEXT,risk TEXT,sample_size INTEGER)""");c.commit()
