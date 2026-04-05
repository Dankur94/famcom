"""Todo module — daily tasks per person, shown in morning summary."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

# todo buy groceries / todo @opa mobbing
_TODO_ADD = re.compile(r'^todo\s+(?:@(\w+)\s+)?(.+)', re.IGNORECASE)
# done 3
_DONE = re.compile(r'^done\s+(\d+)\s*$', re.IGNORECASE)
# delete todo 3
_DELETE = re.compile(r'^delete\s+todo\s+(\d+)\s*$', re.IGNORECASE)


class TodoModule(BaseModule):
    VOICE_INFO = {
        "command": "todo TEXT or todo @person TEXT, done ID, todos",
        "examples": [
            ("add a todo buy groceries", "todo buy groceries"),
            ("todo for opa go to the doctor", "todo @opa go to the doctor"),
            ("mark todo 3 as done", "done 3"),
            ("show all todos", "todos"),
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

    def _resolve_alias(self, alias: str) -> str | None:
        """Resolve @alias to member name."""
        for name, info in self._members.items():
            aliases = [a.lower() for a in info.get("aliases", [])]
            if alias.lower() == name.lower() or alias.lower() in aliases:
                return name
        return None

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t in ("todos", "todo list", "my todos"):
            return True
        if _DONE.match(t):
            return True
        if _DELETE.match(t):
            return True
        if t.startswith("todo "):
            return True
        return False

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()
        tl = t.lower()
        person = self._resolve_sender(message.sender)

        # List todos
        if tl in ("todos", "todo list", "my todos"):
            return self._list_todos()

        # Mark done
        dm = _DONE.match(tl)
        if dm:
            todo_id = int(dm.group(1))
            if self.db.complete_todo(todo_id):
                return Response(f"\u2705 Todo #{todo_id} done!")
            return Response(f"Todo #{todo_id} not found or already done.")

        # Delete todo
        delm = _DELETE.match(tl)
        if delm:
            todo_id = int(delm.group(1))
            self.db.delete_todo(todo_id)
            return Response(f"\U0001f5d1 Deleted todo #{todo_id}")

        # Add todo
        am = _TODO_ADD.match(t)
        if am:
            alias = am.group(1)
            text = am.group(2).strip()
            if alias:
                target = self._resolve_alias(alias)
                if not target:
                    return Response(f"Unknown member: @{alias}")
            else:
                target = person
            entry = self.db.add_todo(target, text)
            return Response(f"\U0001f4cb Todo #{entry['id']} for *{target}*: {text}")

        return None

    def _list_todos(self) -> Response:
        todos = self.db.get_open_todos()
        if not todos:
            return Response("No open todos. Add one with `todo buy groceries`")

        by_person = {}
        for t in todos:
            by_person.setdefault(t["person"], []).append(t)

        lines = ["\U0001f4cb *Open Todos*", ""]
        for person in sorted(by_person.keys()):
            lines.append(f"*{person}:*")
            for t in by_person[person]:
                lines.append(f"  \u2610 #{t['id']} {t['text']}")
            lines.append("")

        return Response("\n".join(lines).strip())

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
