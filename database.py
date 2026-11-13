import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("water_reports.db")

def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS handlers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        role TEXT NOT NULL,
        zone TEXT NOT NULL,
        available INTEGER NOT NULL DEFAULT 1,
        capacity INTEGER NOT NULL DEFAULT 5,
        current_load INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS reports(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        reporter_name TEXT NOT NULL,
        contact TEXT,
        station_code TEXT NOT NULL,
        parameter_code TEXT NOT NULL,
        description TEXT NOT NULL,
        urgency TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        status TEXT NOT NULL,
        validation_message TEXT NOT NULL,
        assigned_handler TEXT,
        route_key TEXT,
        dispatch_note TEXT,
        created_at TEXT NOT NULL
    );
    """)
    count = db.execute("SELECT COUNT(*) n FROM handlers").fetchone()["n"]
    if count == 0:
        seed = [
            ("North Field Team", "Maintenance", "NTH", 1, 5, 0),
            ("South Field Team", "Maintenance", "STH", 1, 5, 0),
            ("East Field Team", "Maintenance", "EST", 1, 5, 0),
            ("West Field Team", "Maintenance", "WST", 1, 5, 0),
            ("Zonal Quality Officer", "Quality Officer", "ALL", 1, 20, 0),
            ("Backup Response Team", "Backup", "ALL", 1, 3, 0)
        ]
        db.executemany("INSERT INTO handlers(name,role,zone,available,capacity,current_load) VALUES(?,?,?,?,?,?)", seed)
    db.commit()
    db.close()
