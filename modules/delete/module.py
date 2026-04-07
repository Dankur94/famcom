"""Delete module — undo last entry or delete by type and time."""

import re
from datetime import datetime, date, timedelta
from modules.base import BaseModule, Message, Response, ScheduledJob

_DELETE_PATTERN = re.compile(
    r'^delete\s+(hurt|smile)\s+(\d{1,2}:\d{2})\s*$',
    re.IGNORECASE
)


class DeleteModule(BaseModule):
    VOICE_INFO = {
        "command": "undo or delete TYPE HH:MM",
        "examples": [
            ("undo", "undo"),
            ("delete the hurt at 14:30", "delete hurt 14:30"),
            ("delete smile at 9", "delete smile 09:00"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t == "undo":
            return True
        return bool(_DELETE_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip().lower()

        if t == "undo":
            return self._undo_last(message.sender)

        match = _DELETE_PATTERN.match(message.text.strip())
        if match:
            entry_type = match.group(1).lower()
            time_str = match.group(2)
            return self._delete_by_time(entry_type, time_str, message.sender)

        return None

    def _undo_last(self, sender: str) -> Response:
        """Delete the most recent entry (hurt or smile) by the sender."""
        candidates = []

        last_ouch = self.db.get_last_ouch()
        if last_ouch and last_ouch["logged_by"] == sender:
            candidates.append(("hurt", last_ouch))

        last_smile = self.db.get_last_smile()
        if last_smile and last_smile["logged_by"] == sender:
            candidates.append(("smile", last_smile))

        if not candidates:
            return Response("Nothing to undo.")

        candidates.sort(key=lambda x: x[1]["timestamp"], reverse=True)
        entry_type, entry = candidates[0]

        if entry_type == "hurt":
            self.db.delete_ouch(entry["id"])
            msg = entry.get("message") or "no message"
            return Response(f"\U0001f5d1 Deleted hurt: {msg}")

        if entry_type == "smile":
            self.db.delete_smile(entry["id"])
            msg = entry.get("message") or "+1"
            return Response(f"\U0001f5d1 Deleted smile: {msg}")

        return Response("Nothing to undo.")

    def _delete_by_time(self, entry_type: str, time_str: str, sender: str) -> Response:
        """Delete entry matching the given type and time (only own entries)."""
        today = date.today()
        h, m = map(int, time_str.split(":"))
        target = datetime(today.year, today.month, today.day, h, m)

        if entry_type == "hurt":
            entries = self.db.get_ouch_today(sender)
        elif entry_type == "smile":
            start = today.isoformat()
            end = (today + timedelta(days=1)).isoformat()
            entries = [e for e in self.db.get_smiles_range(start, end) if e["logged_by"] == sender]
        else:
            return Response(f"Unknown type: {entry_type}")

        # Find entry closest to the target time
        best = None
        best_diff = float("inf")
        for e in entries:
            ts = datetime.fromisoformat(e["timestamp"])
            diff = abs((ts - target).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best = e

        if not best or best_diff > 1800:  # 30 min tolerance
            return Response(f"No {entry_type} found near {time_str} today.")

        ts_display = datetime.fromisoformat(best["timestamp"]).strftime("%H:%M")

        if entry_type == "hurt":
            self.db.delete_ouch(best["id"])
            msg = best.get("message") or ""
            return Response(f"\U0001f5d1 Deleted hurt at {ts_display}: {msg}")
        else:
            self.db.delete_smile(best["id"])
            msg = best.get("message") or "+1"
            return Response(f"\U0001f5d1 Deleted smile at {ts_display}: {msg}")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
