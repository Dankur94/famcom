"""Groceries module — track what food/items were bought."""

import re
from datetime import datetime
from modules.base import BaseModule, Message, Response, ScheduledJob

# Patterns:
# bought milk, eggs, bread
# bought @opa milk, eggs, bread
# gekauft milch, eier, brot
# groceries — show today's list
_BOUGHT_PATTERN = re.compile(
    r'^(?:bought|gekauft|einkauf)\s+(?:@(\w+)\s+)?(.+)\s*$',
    re.IGNORECASE
)


def _resolve_member(alias: str, members: dict) -> str | None:
    alias_lower = alias.lower()
    for name, info in members.items():
        if alias_lower == name.lower():
            return name
        if alias_lower in [a.lower() for a in info.get("aliases", [])]:
            return name
    return None


class GroceriesModule(BaseModule):
    VOICE_INFO = {
        "command": "bought ITEMS or gekauft ITEMS or groceries",
        "examples": [
            ("bought milk eggs and bread", "bought milk, eggs, bread"),
            ("gekauft milch eier brot", "gekauft milch, eier, brot"),
            ("opa hat milch und eier gekauft", "bought @opa milk, eggs"),
            ("babe bought diapers and formula", "bought @babe diapers, formula"),
            ("was haben wir heute gekauft", "groceries"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members: dict):
        self._members = members

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t in ("groceries", "einkaufsliste", "einkauefe", "einkäufe"):
            return True
        return bool(_BOUGHT_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()

        if t.lower() in ("groceries", "einkaufsliste", "einkauefe", "einkäufe"):
            return self._show_today(message.sender)

        match = _BOUGHT_PATTERN.match(t)
        if not match:
            return None

        person_alias = match.group(1)
        items_raw = match.group(2).strip()

        # Resolve @person or use sender
        bought_by = message.sender
        if person_alias and self._members:
            resolved = _resolve_member(person_alias, self._members)
            if resolved:
                bought_by = resolved
            else:
                bought_by = person_alias

        # Split items by comma, "and", "und", or multiple spaces
        items_raw = re.sub(r'\s+and\s+|\s+und\s+', ', ', items_raw, flags=re.IGNORECASE)
        items = [i.strip() for i in items_raw.split(',') if i.strip()]

        if not items:
            return None

        added = []
        for item in items:
            result = self.db.add_grocery_item(
                item=item,
                bought_by=bought_by,
            )
            added.append(result["item"])

        # Today's count
        today_items = self.db.get_groceries_today()

        items_list = ", ".join(added)
        return Response(
            f"🛒 *{bought_by}* bought: {items_list}\n"
            f"📊 Today: {len(today_items)} item(s) total"
        )

    def _show_today(self, sender: str) -> Response:
        today_items = self.db.get_groceries_today()
        if not today_items:
            return Response("🛒 No groceries logged today.")

        # Group by buyer
        by_person = {}
        for item in today_items:
            person = item["bought_by"]
            if person not in by_person:
                by_person[person] = []
            by_person[person].append(item["item"])

        lines = ["🛒 *Today's Groceries:*"]
        for person, items in by_person.items():
            lines.append(f"\n*{person}:*")
            for i in items:
                lines.append(f"  • {i}")

        lines.append(f"\n{len(today_items)} item(s) total")
        return Response("\n".join(lines))

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
