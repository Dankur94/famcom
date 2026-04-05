"""AI Query module — natural language database access via DeepSeek."""

import re
import sqlite3
from openai import OpenAI
from modules.base import BaseModule, Message, Response, ScheduledJob

_SCHEMA = """\
Tables in this SQLite database:

expenses(id, amount_hkd REAL, category TEXT, description TEXT, logged_by TEXT, timestamp TEXT)
time_entries(id, minutes INTEGER, category TEXT, description TEXT, logged_by TEXT, timestamp TEXT)
thanks(id, from_user TEXT, to_user TEXT, message TEXT, timestamp TEXT)
reminders(id, created_by TEXT, remind_at TEXT, message TEXT, is_sent INTEGER, created_at TEXT)
grocery_items(id, item TEXT, quantity TEXT, bought_by TEXT, timestamp TEXT)

All timestamps are ISO format (e.g. 2026-04-05T14:30:00).
Currency is HKD. Time entries are in minutes.
Members: Daniel, Babe, Gerold."""

_SQL_PROMPT = f"""\
You are a SQL assistant for a family tracking app (FamCom).
Given a user question, write a single SQLite SELECT query to answer it.
Return ONLY the SQL query, nothing else. No markdown, no explanation.
If the question cannot be answered with a query, return "NONE".

{_SCHEMA}

Important:
- Use date() and time() functions for date filtering
- For "this week": WHERE timestamp >= date('now', 'weekday 0', '-7 days')
- For "today": WHERE timestamp >= date('now')
- For "this month": WHERE timestamp >= date('now', 'start of month')
- Always ORDER BY timestamp DESC unless asked otherwise
- LIMIT 50 max to avoid huge results
- For DELETE requests: use DELETE FROM table WHERE conditions. Be precise.
- You may use SELECT or DELETE. No UPDATE, INSERT, DROP, or ALTER."""

_FORMAT_PROMPT = """\
You format SQL query results into a clean WhatsApp message.
Keep it concise and readable. Use bullet points or simple tables.
If the result is empty, say "No results found."
Do NOT use markdown code blocks. Use WhatsApp formatting: *bold*, _italic_.
Answer in the same language as the user's question."""


class AIQueryModule(BaseModule):
    VOICE_INFO = {
        "command": "!q QUESTION (AI database query)",
        "examples": [
            ("show me all expenses this week", "!q all expenses this week"),
            ("wer hat am meisten ausgegeben", "!q wer hat am meisten ausgegeben"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._client = None
        self._model = "deepseek-chat"

    def _get_client(self):
        if not self._client:
            api_key = self.config.get("api_key", "")
            base_url = self.config.get("base_url", "https://api.deepseek.com")
            self._model = self.config.get("model", "deepseek-chat")
            self._client = OpenAI(api_key=api_key, base_url=base_url)
        return self._client

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip()
        return t.startswith("!q ") or t.startswith("!q:")

    def handle(self, message: Message) -> Response | None:
        question = message.text.strip()[2:].strip().lstrip(":")
        if not question:
            return Response("Usage: `!q your question here`\nExample: `!q show all expenses this week`")

        try:
            # Step 1: Generate SQL
            client = self._get_client()
            sql_response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SQL_PROMPT},
                    {"role": "user", "content": question},
                ],
                max_tokens=300,
                temperature=0,
            )
            sql = sql_response.choices[0].message.content.strip()

            if sql.upper() == "NONE":
                return Response("I can't answer that with a database query.")

            # Safety: only allow SELECT and DELETE
            sql_upper = sql.upper().strip()
            if not (sql_upper.startswith("SELECT") or sql_upper.startswith("DELETE")):
                return Response("Only SELECT and DELETE queries are allowed.")

            # Step 2: Execute query
            cursor = self.db.conn.cursor()
            cursor.execute(sql)

            if sql_upper.startswith("DELETE"):
                affected = cursor.rowcount
                self.db.conn.commit()
                return Response(f"\U0001f916 Deleted {affected} row(s).")

            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()

            if not rows:
                result_text = "No results found."
            else:
                # Format as text table
                lines = [" | ".join(columns)]
                for row in rows[:50]:
                    lines.append(" | ".join(str(v) for v in row))
                result_text = "\n".join(lines)

            # Step 3: Format nicely via AI
            format_response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _FORMAT_PROMPT},
                    {"role": "user", "content": f"User asked: {question}\n\nSQL result:\n{result_text}"},
                ],
                max_tokens=500,
                temperature=0,
            )
            formatted = format_response.choices[0].message.content.strip()

            return Response(f"\U0001f916 {formatted}")

        except sqlite3.Error as e:
            return Response(f"\u26a0\ufe0f SQL error: {e}")
        except Exception as e:
            return Response(f"\u26a0\ufe0f AI error: {e}")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
