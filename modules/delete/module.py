"""Delete module — undo last entry or delete by type and time."""

import re
from datetime import datetime
from modules.base import BaseModule, Message, Response, ScheduledJob

# Patterns:
# undo — delete the most recent entry (any type)
# delete expense 14:30 — delete expense at that time
# delete time 09:00 — delete time entry at that time
_DELETE_PATTERN = re.compile(
    r'^delete\s+(expense|time)\s+(\d{1,2}:\d{2})\s*$',
    re.IGNORECASE
)


class DeleteModule(BaseModule):
    VOICE_INFO = {
        "command": "undo or delete TYPE HH:MM",
        "examples": [
            ("undo", "undo"),
            ("delete the expense at 14:30", "delete expense 14:30"),
            ("delete time entry at 9", "delete time 09:00"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t == "undo":
            return True
        if _DELETE_PATTERN.match(message.text.strip()):
            return True
        # "delete todo N" is handled by TodoModule, not here
        return False

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip().lower()

        if t == "undo":
            return self._undo_last()

        match = _DELETE_PATTERN.match(message.text.strip())
        if match:
            entry_type = match.group(1).lower()
            time_str = match.group(2)
            return self._delete_by_time(entry_type, time_str)

        return None

    def _undo_last(self) -> Response:
        """Delete the most recent entry across all types."""
        candidates = []

        last_expense = self.db.get_last_expense()
        if last_expense:
            candidates.append(("expense", last_expense))

        last_time = self.db.get_last_time_entry()
        if last_time:
            candidates.append(("time", last_time))

        last_grocery = self.db.get_last_grocery()
        if last_grocery:
            candidates.append(("grocery", last_grocery))

        last_ouch = self.db.get_last_ouch()
        if last_ouch:
            candidates.append(("ouch", last_ouch))

        last_pain = self.db.get_last_pain()
        if last_pain:
            candidates.append(("pain", last_pain))

        last_asset = self.db.get_last_asset()
        if last_asset:
            candidates.append(("asset", last_asset))

        if not candidates:
            return Response("Nothing to undo.")

        # Find the most recent (assets use created_at instead of timestamp)
        candidates.sort(key=lambda x: x[1].get("timestamp") or x[1].get("created_at", ""), reverse=True)
        entry_type, entry = candidates[0]

        if entry_type == "grocery":
            self.db.delete_grocery(entry["id"])
            return Response(f"🗑 Deleted grocery: {entry['item']}")

        if entry_type == "ouch":
            self.db.delete_ouch(entry["id"])
            msg = entry.get("message") or "no message"
            return Response(f"🗑 Deleted ouch: {msg}")

        if entry_type == "pain":
            self.db.delete_pain(entry["id"])
            msg = entry.get("message") or "no message"
            return Response(f"🗑 Deleted pain: {msg}")

        if entry_type == "asset":
            self.db.delete_asset(entry["id"])
            return Response(f"🗑 Deleted asset: {entry['description']}")

        self.db.delete_entry(entry_type, entry["id"])

        if entry_type == "expense":
            return Response(f"🗑 Deleted expense: ${entry['amount_hkd']:.0f} {entry['description']}")
        else:
            mins = entry["minutes"]
            dur = f"{mins / 60:.1f}h" if mins >= 60 else f"{mins}min"
            return Response(f"🗑 Deleted time: {dur} {entry['description']}")

    def _delete_by_time(self, entry_type: str, time_str: str) -> Response:
        """Delete entry matching the given type and time."""
        from datetime import date
        target_prefix = datetime.combine(date.today(), datetime.min.time())
        h, m = map(int, time_str.split(":"))
        target_ts = target_prefix.replace(hour=h, minute=m).isoformat()

        if entry_type == "expense":
            entries = self.db.get_expenses_today()
        elif entry_type == "time":
            entries = self.db.get_time_entries_today()
        else:
            return Response(f"Unknown type: {entry_type}")

        # Find entry closest to the target time
        best = None
        best_diff = float("inf")
        for e in entries:
            ts = datetime.fromisoformat(e["timestamp"])
            target = datetime.fromisoformat(target_ts)
            diff = abs((ts - target).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best = e

        if not best or best_diff > 1800:  # 30 min tolerance
            return Response(f"No {entry_type} found near {time_str} today.")

        self.db.delete_entry(entry_type, best["id"])

        ts_display = datetime.fromisoformat(best["timestamp"]).strftime("%H:%M")
        if entry_type == "expense":
            return Response(f"🗑 Deleted expense at {ts_display}: ${best['amount_hkd']:.0f} {best['description']}")
        else:
            mins = best["minutes"]
            dur = f"{mins / 60:.1f}h" if mins >= 60 else f"{mins}min"
            return Response(f"🗑 Deleted time at {ts_display}: {dur} {best['description']}")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
