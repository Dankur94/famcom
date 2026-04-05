"""Time log module — track time investments."""

import re
from datetime import datetime
from modules.base import BaseModule, Message, Response, ScheduledJob

# Keyword → category mapping
CATEGORY_MAP = {
    "cooking": "cooking", "kochen": "cooking", "cook": "cooking",
    "cleaning": "cleaning", "putzen": "cleaning", "clean": "cleaning",
    "sauber": "cleaning", "aufraumen": "cleaning",
    "shopping": "shopping", "einkaufen": "shopping",
    "laundry": "laundry", "waesche": "laundry", "waschen": "laundry",
    "ironing": "laundry", "buegeln": "laundry",
    "gardening": "gardening", "garten": "gardening",
    "repair": "repair", "reparatur": "repair", "fix": "repair",
    "childcare": "childcare", "babysitting": "childcare", "baby": "childcare",
    "spielen": "childcare", "playing": "childcare",
    "driving": "driving", "fahren": "driving", "pickup": "driving",
    "errands": "errands", "besorgung": "errands",
    "work": "work", "arbeit": "work", "office": "work", "buero": "work",
}


def detect_category(description: str) -> str:
    words = description.lower().split()
    for word in words:
        if word in CATEGORY_MAP:
            return CATEGORY_MAP[word]
    return "other"


def _resolve_member(alias: str, members: dict) -> str | None:
    """Resolve an alias like 'babe', 'opa' to the member's display name."""
    alias_lower = alias.lower()
    for name, info in members.items():
        if alias_lower == name.lower():
            return name
        if alias_lower in [a.lower() for a in info.get("aliases", [])]:
            return name
    return None


# Pattern: 2h cooking | 30min cleaning @babe | 1.5h gardening @opa 09:00
_TIME_PATTERN = re.compile(
    r'^(\d+(?:\.\d+)?)\s*(h|hr|hrs|hour|hours|stunden?|min|mins|minutes?|minuten?)\s+(.+?)(?:\s+@(\w+))?(?:\s+(\d{1,2}:\d{2}))?\s*$',
    re.IGNORECASE
)


class TimeLogModule(BaseModule):
    VOICE_INFO = {
        "command": "Xh DESCRIPTION or Xmin DESCRIPTION @PERSON",
        "examples": [
            ("two hours cooking", "2h cooking"),
            ("thirty minutes cleaning", "30min cleaning"),
            ("eine stunde kochen", "1h cooking"),
            ("half an hour of laundry", "30min laundry"),
            ("babe hat 2 stunden geputzt", "2h cleaning @babe"),
            ("opa hat 1 stunde gekocht", "1h cooking @opa"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members: dict):
        self._members = members

    def can_handle(self, message: Message) -> bool:
        return bool(_TIME_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _TIME_PATTERN.match(message.text.strip())
        if not match:
            return None

        amount = float(match.group(1))
        unit = match.group(2).lower()
        description = match.group(3).strip()
        person_alias = match.group(4)
        time_str = match.group(5)

        # Convert to minutes
        if unit.startswith(("h", "s")):  # h, hr, hrs, hour, stunde
            minutes = int(amount * 60)
        else:
            minutes = int(amount)

        category = detect_category(description)

        # Resolve @person or use sender
        logged_by = message.sender
        if person_alias and self._members:
            resolved = _resolve_member(person_alias, self._members)
            if resolved:
                logged_by = resolved
            else:
                logged_by = person_alias

        # Build timestamp
        ts = None
        if time_str:
            h, m = map(int, time_str.split(":"))
            from datetime import date
            ts = datetime.combine(date.today(), datetime.min.time()).replace(hour=h, minute=m).isoformat()

        result = self.db.add_time_entry(
            minutes=minutes,
            category=category,
            description=description,
            logged_by=logged_by,
            timestamp=ts,
        )

        t_display = datetime.fromisoformat(result["timestamp"]).strftime("%H:%M")
        cat_display = f" [{category}]" if category != "other" else ""

        # Format duration
        if minutes >= 60:
            dur = f"{minutes / 60:.1f}h"
        else:
            dur = f"{minutes}min"

        # Today's total
        today_entries = self.db.get_time_entries_today()
        today_total = sum(e["minutes"] for e in today_entries)
        today_hrs = f"{today_total / 60:.1f}h" if today_total >= 60 else f"{today_total}min"

        return Response(
            f"⏱ *{dur}* {description}{cat_display}\n"
            f"🕐 {t_display} by {logged_by}\n"
            f"📊 Today: {today_hrs} in {len(today_entries)} entry/entries"
        )

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
