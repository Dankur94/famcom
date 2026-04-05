"""Assets module — track major family asset contributions."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

# asset house germany 5000000
# asset @opa real estate berlin 5M
# asset car toyota 250k
_ASSET_PATTERN = re.compile(
    r'^asset\s+(?:@(\w+)\s+)?(.+?)\s+(\d+(?:\.\d+)?)\s*([kmb]?)$',
    re.IGNORECASE
)


def _parse_value(num_str: str, suffix: str) -> float:
    """Parse '5M' -> 5000000, '250k' -> 250000, '1.5b' -> 1500000000."""
    val = float(num_str)
    s = suffix.lower()
    if s == 'k':
        return val * 1_000
    elif s == 'm':
        return val * 1_000_000
    elif s == 'b':
        return val * 1_000_000_000
    return val


def _fmt_value(amount: float) -> str:
    """Format large numbers: 5000000 -> $5.0M, 250000 -> $250k."""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}k"
    return f"${amount:,.0f}"


class AssetsModule(BaseModule):
    VOICE_INFO = {
        "command": "asset DESCRIPTION VALUE or assets to list",
        "examples": [
            ("asset house germany 5M", "asset house germany 5M"),
            ("asset car toyota 250k", "asset car toyota 250k"),
            ("asset for opa real estate berlin 5M", "asset @opa real estate berlin 5M"),
            ("show all assets", "assets"),
            ("delete asset 1", "delete asset 1"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members_config: dict):
        self._members = members_config

    def _resolve_member(self, alias: str) -> str | None:
        alias_lower = alias.lower()
        for name, info in self._members.items():
            if alias_lower == name.lower():
                return name
            if alias_lower in [a.lower() for a in info.get("aliases", [])]:
                return name
        return None

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t in ("assets", "my assets"):
            return True
        if re.match(r'^delete\s+asset\s+\d+\s*$', t, re.IGNORECASE):
            return True
        if t.startswith("asset "):
            return True
        return False

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()
        tl = t.lower()

        # List assets
        if tl in ("assets", "my assets"):
            return self._list_assets()

        # Delete asset
        dm = re.match(r'^delete\s+asset\s+(\d+)\s*$', t, re.IGNORECASE)
        if dm:
            asset_id = int(dm.group(1))
            assets = self.db.get_assets()
            if any(a["id"] == asset_id for a in assets):
                self.db.delete_asset(asset_id)
                return Response(f"\U0001f5d1 Deleted asset #{asset_id}")
            return Response(f"Asset #{asset_id} not found.")

        # Add asset
        match = _ASSET_PATTERN.match(t)
        if not match:
            return Response("Usage: `asset house germany 5M`\nSupports k (thousands), M (millions), B (billions)")

        person_alias = match.group(1)
        description = match.group(2).strip()
        value = _parse_value(match.group(3), match.group(4))

        # Resolve person
        person = message.sender
        if person_alias:
            resolved = self._resolve_member(person_alias)
            person = resolved or person_alias

        entry = self.db.add_asset(person, description, value)

        # Total assets
        all_assets = self.db.get_assets()
        total = sum(a["value_hkd"] for a in all_assets)

        return Response(
            f"\U0001f3e0 Asset #{entry['id']}: *{description}* — {_fmt_value(value)}\n"
            f"   by *{person}*\n"
            f"\U0001f4b0 Total family assets: {_fmt_value(total)}"
        )

    def _list_assets(self) -> Response:
        assets = self.db.get_assets()
        if not assets:
            return Response("No assets registered. Add one with `asset house germany 5M`")

        total = sum(a["value_hkd"] for a in assets)

        # Group by person
        by_person = {}
        for a in assets:
            by_person.setdefault(a["person"], []).append(a)

        lines = [f"\U0001f3e0 *Family Assets* — {_fmt_value(total)}", ""]

        for person in sorted(by_person):
            person_total = sum(a["value_hkd"] for a in by_person[person])
            pct = (person_total / total * 100) if total > 0 else 0
            lines.append(f"\U0001f464 *{person}* — {_fmt_value(person_total)} ({pct:.0f}%)")
            for a in by_person[person]:
                lines.append(f"  #{a['id']} {a['description']} — {_fmt_value(a['value_hkd'])}")
            lines.append("")

        return Response("\n".join(lines).strip())

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
