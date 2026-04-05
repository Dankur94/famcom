"""Expense module — track family expenses in HKD."""

import re
from datetime import datetime
from modules.base import BaseModule, Message, Response, ScheduledJob

# Keyword → category mapping (no AI needed)
CATEGORY_MAP = {
    "groceries": "groceries", "grocery": "groceries", "supermarket": "groceries",
    "food": "groceries", "lebensmittel": "groceries", "essen": "groceries",
    "einkauf": "groceries",
    "taxi": "transport", "uber": "transport", "bus": "transport",
    "mtr": "transport", "transport": "transport", "fahrt": "transport",
    "gas": "transport", "petrol": "transport", "benzin": "transport",
    "lunch": "dining", "dinner": "dining", "breakfast": "dining",
    "restaurant": "dining", "cafe": "dining", "coffee": "dining",
    "kaffee": "dining", "mittag": "dining", "abendessen": "dining",
    "rent": "housing", "miete": "housing", "electricity": "housing",
    "strom": "housing", "water": "housing", "wasser": "housing",
    "internet": "housing", "wifi": "housing",
    "doctor": "health", "arzt": "health", "medicine": "health",
    "medizin": "health", "pharmacy": "health", "apotheke": "health",
    "hospital": "health",
    "clothes": "shopping", "kleidung": "shopping", "shoes": "shopping",
    "schuhe": "shopping", "amazon": "shopping",
    "baby": "baby", "diapers": "baby", "windeln": "baby",
    "formula": "baby", "milch": "baby",
    "gift": "gifts", "geschenk": "gifts", "present": "gifts",
}


def detect_category(description: str) -> str:
    """Detect category from description keywords."""
    words = description.lower().split()
    for word in words:
        if word in CATEGORY_MAP:
            return CATEGORY_MAP[word]
    return "other"


# Pattern: $50 groceries | expense 150 taxi | $30.50 lunch @babe | $50 rent @wife 14:30
_DOLLAR_PATTERN = re.compile(
    r'^\$\s*(\d+(?:\.\d{1,2})?)\s+(.+?)(?:\s+@(\w+))?(?:\s+(\d{1,2}:\d{2}))?\s*$',
    re.IGNORECASE
)
_EXPENSE_PATTERN = re.compile(
    r'^expense\s+(\d+(?:\.\d{1,2})?)\s+(.+?)(?:\s+@(\w+))?(?:\s+(\d{1,2}:\d{2}))?\s*$',
    re.IGNORECASE
)


def _resolve_member(alias: str, members: dict) -> str | None:
    """Resolve an alias like 'babe', 'opa' to the member's display name."""
    alias_lower = alias.lower()
    for name, info in members.items():
        if alias_lower == name.lower():
            return name
        if alias_lower in [a.lower() for a in info.get("aliases", [])]:
            return name
    return None


class ExpenseModule(BaseModule):
    VOICE_INFO = {
        "command": "$AMOUNT DESCRIPTION or $AMOUNT DESCRIPTION @PERSON",
        "examples": [
            ("fifty dollars for groceries", "$50 groceries"),
            ("spent 150 on a taxi", "$150 taxi"),
            ("ich hab 30 dollar fuer essen ausgegeben", "$30 lunch"),
            ("paid 200 for dinner", "$200 dinner"),
            ("babe pays 15000 for rent", "$15000 rent @babe"),
            ("opa hat 500 fuer groceries ausgegeben", "$500 groceries @opa"),
            ("meine frau gibt 15000 fuer miete aus", "$15000 rent @babe"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        # Members config is passed via config from server
        self._members = {}

    def set_members(self, members: dict):
        self._members = members

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip()
        return bool(_DOLLAR_PATTERN.match(t) or _EXPENSE_PATTERN.match(t))

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()

        match = _DOLLAR_PATTERN.match(t) or _EXPENSE_PATTERN.match(t)
        if not match:
            return None

        amount = float(match.group(1))
        description = match.group(2).strip()
        person_alias = match.group(3)
        time_str = match.group(4)

        category = detect_category(description)

        # Resolve @person or use sender
        logged_by = message.sender
        if person_alias and self._members:
            resolved = _resolve_member(person_alias, self._members)
            if resolved:
                logged_by = resolved
            else:
                logged_by = person_alias  # use alias as-is if not in config

        # Build timestamp
        ts = None
        if time_str:
            h, m = map(int, time_str.split(":"))
            from datetime import date
            ts = datetime.combine(date.today(), datetime.min.time()).replace(hour=h, minute=m).isoformat()

        result = self.db.add_expense(
            amount_hkd=amount,
            category=category,
            description=description,
            logged_by=logged_by,
            timestamp=ts,
        )

        t_display = datetime.fromisoformat(result["timestamp"]).strftime("%H:%M")
        cat_display = f" [{category}]" if category != "other" else ""

        # Today's total
        today_expenses = self.db.get_expenses_today()
        today_total = sum(e["amount_hkd"] for e in today_expenses)

        return Response(
            f"💰 *${amount:.0f}* for {description}{cat_display}\n"
            f"🕐 {t_display} by {logged_by}\n"
            f"📊 Today: ${today_total:.0f} in {len(today_expenses)} expense(s)"
        )

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
