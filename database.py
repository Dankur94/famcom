"""SQLite database layer for HeartSync."""

import sqlite3
from datetime import datetime, date, timedelta


class Database:
    def __init__(self, path: str = "heartsync.db"):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ouch_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_by TEXT NOT NULL,
                about_user TEXT,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_by TEXT NOT NULL,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        self.conn.commit()

    # --- Ouch (Hurt) Entries ---

    def add_ouch(self, logged_by: str, about_user: str = None,
                 message: str = None, timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO ouch_entries (logged_by, about_user, message, timestamp) VALUES (?, ?, ?, ?)",
            (logged_by, about_user, message, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "logged_by": logged_by, "about_user": about_user,
                "message": message, "timestamp": ts}

    def get_ouch_today(self, person: str) -> list[dict]:
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM ouch_entries WHERE logged_by = ? AND timestamp >= ? ORDER BY timestamp",
            (person, today)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_ouch_alltime(self, person: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ouch_entries WHERE logged_by = ?", (person,))
        return cursor.fetchone()[0]

    def get_ouch_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ouch_entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def get_last_ouch(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ouch_entries ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_ouch(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM ouch_entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_ouch_today_by_person(self, start: str, end: str) -> dict:
        """Ouch entries per person for a date range."""
        entries = self.get_ouch_range(start, end)
        result = {}
        for e in entries:
            person = e["logged_by"]
            result.setdefault(person, []).append(e)
        return result

    # --- Smile Entries ---

    def add_smile(self, logged_by: str, message: str = None,
                  timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO smiles (logged_by, message, timestamp) VALUES (?, ?, ?)",
            (logged_by, message, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "logged_by": logged_by,
                "message": message, "timestamp": ts}

    def get_smiles_today(self, person: str) -> int:
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM smiles WHERE logged_by = ? AND timestamp >= ?",
            (person, today)
        )
        return cursor.fetchone()[0]

    def get_smiles_alltime(self, person: str) -> int:
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM smiles WHERE logged_by = ?", (person,))
        return cursor.fetchone()[0]

    def get_last_smile(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM smiles ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_smile(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM smiles WHERE id = ?", (entry_id,))
        self.conn.commit()

    def get_smiles_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM smiles WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
