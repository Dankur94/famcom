"""SQLite database layer for FamCom."""

import sqlite3
from datetime import datetime, date, timedelta


class Database:
    def __init__(self, path: str = "famcom.db"):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount_hkd REAL NOT NULL,
                category TEXT NOT NULL DEFAULT 'other',
                description TEXT NOT NULL,
                logged_by TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minutes INTEGER NOT NULL,
                category TEXT NOT NULL DEFAULT 'other',
                description TEXT NOT NULL,
                logged_by TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS thanks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user TEXT NOT NULL,
                to_user TEXT NOT NULL,
                message TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_by TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                message TEXT NOT NULL,
                is_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS grocery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item TEXT NOT NULL,
                quantity TEXT,
                bought_by TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ouch_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                logged_by TEXT NOT NULL,
                about_user TEXT,
                message TEXT,
                timestamp TEXT NOT NULL
            )
        """)

        self.conn.commit()

    # --- Grocery Items ---

    def add_grocery_item(self, item: str, bought_by: str, quantity: str = None,
                         timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO grocery_items (item, quantity, bought_by, timestamp) VALUES (?, ?, ?, ?)",
            (item.strip(), quantity, bought_by, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "item": item.strip(), "quantity": quantity,
                "bought_by": bought_by, "timestamp": ts}

    def get_groceries_today(self) -> list[dict]:
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM grocery_items WHERE timestamp >= ? ORDER BY timestamp", (today,))
        return [dict(row) for row in cursor.fetchall()]

    def get_groceries_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM grocery_items WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def get_last_grocery(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM grocery_items ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_grocery(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM grocery_items WHERE id = ?", (entry_id,))
        self.conn.commit()

    # --- Ouch Entries ---

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

    def get_all_ouch_by_person(self) -> dict:
        """All-time ouch entries per person (logged_by)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM ouch_entries ORDER BY timestamp")
        entries = [dict(row) for row in cursor.fetchall()]
        result = {}
        for e in entries:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"count": 0, "about": {}}
            result[person]["count"] += 1
            about = e["about_user"]
            if about:
                result[person]["about"][about] = result[person]["about"].get(about, 0) + 1
        return result

    def get_ouch_by_person(self, start: str, end: str) -> dict:
        """Ouch entries per person for a date range."""
        entries = self.get_ouch_range(start, end)
        result = {}
        for e in entries:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"count": 0, "about": {}}
            result[person]["count"] += 1
            about = e["about_user"]
            if about:
                result[person]["about"][about] = result[person]["about"].get(about, 0) + 1
        return result

    # --- Expenses ---

    def add_expense(self, amount_hkd: float, category: str, description: str,
                    logged_by: str, timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO expenses (amount_hkd, category, description, logged_by, timestamp) VALUES (?, ?, ?, ?, ?)",
            (amount_hkd, category, description, logged_by, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "amount_hkd": amount_hkd, "category": category,
                "description": description, "logged_by": logged_by, "timestamp": ts}

    def get_expenses_today(self) -> list[dict]:
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE timestamp >= ? ORDER BY timestamp", (today,))
        return [dict(row) for row in cursor.fetchall()]

    def get_expenses_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM expenses WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def get_last_expense(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM expenses ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_expense(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (entry_id,))
        self.conn.commit()

    # --- Time Entries ---

    def add_time_entry(self, minutes: int, category: str, description: str,
                       logged_by: str, timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO time_entries (minutes, category, description, logged_by, timestamp) VALUES (?, ?, ?, ?, ?)",
            (minutes, category, description, logged_by, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "minutes": minutes, "category": category,
                "description": description, "logged_by": logged_by, "timestamp": ts}

    def get_time_entries_today(self) -> list[dict]:
        today = date.today().isoformat()
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM time_entries WHERE timestamp >= ? ORDER BY timestamp", (today,))
        return [dict(row) for row in cursor.fetchall()]

    def get_time_entries_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM time_entries WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def get_last_time_entry(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM time_entries ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_time_entry(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM time_entries WHERE id = ?", (entry_id,))
        self.conn.commit()

    # --- Thanks ---

    def add_thanks(self, from_user: str, to_user: str, message: str,
                   timestamp: str = None) -> dict:
        ts = timestamp or datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO thanks (from_user, to_user, message, timestamp) VALUES (?, ?, ?, ?)",
            (from_user, to_user, message, ts)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "from_user": from_user, "to_user": to_user,
                "message": message, "timestamp": ts}

    def get_thanks_range(self, start: str, end: str) -> list[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM thanks WHERE timestamp >= ? AND timestamp < ? ORDER BY timestamp",
                       (start, end))
        return [dict(row) for row in cursor.fetchall()]

    def get_last_thanks(self) -> dict | None:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM thanks ORDER BY timestamp DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None

    def delete_thanks(self, entry_id: int):
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM thanks WHERE id = ?", (entry_id,))
        self.conn.commit()

    # --- Reminders ---

    def add_reminder(self, created_by: str, remind_at: str, message: str) -> dict:
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO reminders (created_by, remind_at, message, is_sent, created_at) VALUES (?, ?, ?, 0, ?)",
            (created_by, remind_at, message, now)
        )
        self.conn.commit()
        return {"id": cursor.lastrowid, "created_by": created_by, "remind_at": remind_at,
                "message": message}

    def get_pending_reminders(self) -> list[dict]:
        """Get all unsent reminders where remind_at <= now."""
        now = datetime.now().isoformat()
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM reminders WHERE is_sent = 0 AND remind_at <= ? ORDER BY remind_at",
            (now,)
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_reminders(self, created_by: str = None) -> list[dict]:
        """Get all unsent future reminders."""
        cursor = self.conn.cursor()
        if created_by:
            cursor.execute(
                "SELECT * FROM reminders WHERE is_sent = 0 AND created_by = ? ORDER BY remind_at",
                (created_by,)
            )
        else:
            cursor.execute("SELECT * FROM reminders WHERE is_sent = 0 ORDER BY remind_at")
        return [dict(row) for row in cursor.fetchall()]

    def mark_reminder_sent(self, reminder_id: int):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
        self.conn.commit()

    # --- Delete generic ---

    def delete_entry(self, entry_type: str, entry_id: int):
        table_map = {"expense": "expenses", "time": "time_entries", "thanks": "thanks"}
        table = table_map.get(entry_type)
        if not table:
            return
        cursor = self.conn.cursor()
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (entry_id,))
        self.conn.commit()

    # --- Aggregation helpers ---

    def get_expenses_by_person(self, start: str, end: str) -> dict:
        """Returns {person: {total: X, count: N, categories: {cat: amount}}}."""
        expenses = self.get_expenses_range(start, end)
        result = {}
        for e in expenses:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"total": 0, "count": 0, "categories": {}}
            result[person]["total"] += e["amount_hkd"]
            result[person]["count"] += 1
            cat = e["category"]
            result[person]["categories"][cat] = result[person]["categories"].get(cat, 0) + e["amount_hkd"]
        return result

    def get_time_by_person(self, start: str, end: str) -> dict:
        """Returns {person: {total_min: X, count: N, categories: {cat: minutes}}}."""
        entries = self.get_time_entries_range(start, end)
        result = {}
        for e in entries:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"total_min": 0, "count": 0, "categories": {}}
            result[person]["total_min"] += e["minutes"]
            result[person]["count"] += 1
            cat = e["category"]
            result[person]["categories"][cat] = result[person]["categories"].get(cat, 0) + e["minutes"]
        return result

    def get_thanks_by_person(self, start: str, end: str) -> dict:
        """Returns {to_person: {count: N, from: {person: count}}}."""
        entries = self.get_thanks_range(start, end)
        result = {}
        for e in entries:
            to = e["to_user"]
            if to not in result:
                result[to] = {"count": 0, "from": {}}
            result[to]["count"] += 1
            fr = e["from_user"]
            result[to]["from"][fr] = result[to]["from"].get(fr, 0) + 1
        return result

    # --- All-time aggregation ---

    def get_all_expenses_by_person(self) -> dict:
        """All-time expenses per person."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM expenses ORDER BY timestamp")
        expenses = [dict(row) for row in cursor.fetchall()]
        result = {}
        for e in expenses:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"total": 0, "count": 0, "categories": {}}
            result[person]["total"] += e["amount_hkd"]
            result[person]["count"] += 1
            cat = e["category"]
            result[person]["categories"][cat] = result[person]["categories"].get(cat, 0) + e["amount_hkd"]
        return result

    def get_all_time_by_person(self) -> dict:
        """All-time time entries per person."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM time_entries ORDER BY timestamp")
        entries = [dict(row) for row in cursor.fetchall()]
        result = {}
        for e in entries:
            person = e["logged_by"]
            if person not in result:
                result[person] = {"total_min": 0, "count": 0, "categories": {}}
            result[person]["total_min"] += e["minutes"]
            result[person]["count"] += 1
            cat = e["category"]
            result[person]["categories"][cat] = result[person]["categories"].get(cat, 0) + e["minutes"]
        return result

    def get_all_thanks_by_person(self) -> dict:
        """All-time thanks per person."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM thanks ORDER BY timestamp")
        entries = [dict(row) for row in cursor.fetchall()]
        result = {}
        for e in entries:
            to = e["to_user"]
            if to not in result:
                result[to] = {"count": 0, "from": {}}
            result[to]["count"] += 1
            fr = e["from_user"]
            result[to]["from"][fr] = result[to]["from"].get(fr, 0) + 1
        return result

    def get_first_entry_date(self) -> str | None:
        """Get the earliest timestamp across all tables."""
        cursor = self.conn.cursor()
        dates = []
        for table, col in [("expenses", "timestamp"), ("time_entries", "timestamp"), ("thanks", "timestamp")]:
            cursor.execute(f"SELECT MIN({col}) FROM {table}")
            row = cursor.fetchone()
            if row and row[0]:
                dates.append(row[0])
        return min(dates) if dates else None

    def close(self):
        self.conn.close()
