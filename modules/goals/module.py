"""Goals & Maxims module — personal goals and life principles."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

# goal save 10k this year
_GOAL_ADD = re.compile(r'^goal\s+(.+)', re.IGNORECASE)
# maxim always be honest
_MAXIM_ADD = re.compile(r'^maxim\s+(.+)', re.IGNORECASE)
# delete goal 2 / delete maxim 1
_DELETE = re.compile(r'^delete\s+(goal|maxim)\s+(\d+)\s*$', re.IGNORECASE)


class GoalsModule(BaseModule):
    VOICE_INFO = {
        "command": "goal/maxim TEXT or goals/maxims to list",
        "examples": [
            ("goal save 10k this year", "goal save 10k this year"),
            ("maxim always be honest", "maxim always be honest"),
            ("show my goals", "goals"),
            ("show my maxims", "maxims"),
            ("delete goal 2", "delete goal 2"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members_config: dict):
        self._members = members_config

    def _resolve_sender(self, sender: str) -> str:
        """Map sender phone name to member name."""
        for name, info in self._members.items():
            aliases = [a.lower() for a in info.get("aliases", [])]
            if sender.lower() == name.lower() or sender.lower() in aliases:
                return name
        return sender

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t in ("goals", "maxims", "my goals", "my maxims"):
            return True
        if _DELETE.match(message.text.strip()):
            return True
        if t.startswith("goal ") or t.startswith("maxim "):
            return True
        return False

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()
        tl = t.lower()
        person = self._resolve_sender(message.sender)

        # List goals
        if tl in ("goals", "my goals"):
            return self._list_goals(person)

        # List maxims
        if tl in ("maxims", "my maxims"):
            return self._list_maxims(person)

        # Delete goal/maxim
        dm = _DELETE.match(t)
        if dm:
            dtype = dm.group(1).lower()
            idx = int(dm.group(2))
            return self._delete_entry(person, dtype, idx)

        # Add goal
        gm = _GOAL_ADD.match(t)
        if gm:
            text = gm.group(1).strip()
            entry = self.db.add_goal(person, text)
            return Response(f"\U0001f3af Goal #{entry['id']} added: {text}")

        # Add maxim
        mm = _MAXIM_ADD.match(t)
        if mm:
            text = mm.group(1).strip()
            entry = self.db.add_maxim(person, text)
            return Response(f"\u2728 Maxim #{entry['id']} added: {text}")

        return None

    def _list_goals(self, person: str) -> Response:
        goals = self.db.get_goals(person)
        if not goals:
            return Response(f"No goals set for *{person}*. Add one with `goal save 10k this year`")
        lines = [f"\U0001f3af *{person}'s Goals*", ""]
        for g in goals:
            lines.append(f"  {g['id']}. {g['text']}")
        return Response("\n".join(lines))

    def _list_maxims(self, person: str) -> Response:
        maxims = self.db.get_maxims(person)
        if not maxims:
            return Response(f"No maxims set for *{person}*. Add one with `maxim always be honest`")
        lines = [f"\u2728 *{person}'s Maxims*", ""]
        for m in maxims:
            lines.append(f"  {m['id']}. {m['text']}")
        return Response("\n".join(lines))

    def _delete_entry(self, person: str, dtype: str, entry_id: int) -> Response:
        if dtype == "goal":
            goals = self.db.get_goals(person)
            if any(g["id"] == entry_id for g in goals):
                self.db.delete_goal(entry_id)
                return Response(f"\U0001f5d1 Deleted goal #{entry_id}")
            return Response(f"Goal #{entry_id} not found for *{person}*.")
        else:
            maxims = self.db.get_maxims(person)
            if any(m["id"] == entry_id for m in maxims):
                self.db.delete_maxim(entry_id)
                return Response(f"\U0001f5d1 Deleted maxim #{entry_id}")
            return Response(f"Maxim #{entry_id} not found for *{person}*.")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
