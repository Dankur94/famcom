"""Reports module — personal daily reports for each member."""

import re
from datetime import datetime, date, timedelta
from modules.base import BaseModule, Message, Response, ScheduledJob


def _truncate(text: str, maxlen: int = 35) -> str:
    """Truncate to ~1 iPhone WhatsApp line."""
    if len(text) <= maxlen:
        return text
    return text[:maxlen - 1].rstrip() + "\u2026"


class ReportsModule(BaseModule):
    VOICE_INFO = {
        "command": "report or today or status",
        "examples": [
            ("how is today looking", "today"),
            ("show me my report", "report"),
            ("status", "status"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members_config: dict):
        self._members = members_config

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        return t in ("report", "today", "status")

    def handle(self, message: Message) -> Response | None:
        parts = []
        for person, info in self._members.items():
            label = info.get("label", person) if isinstance(info, dict) else person
            parts.append(self._build_personal_report(person, label))
        divider = chr(10)*2 + chr(9473)*15 + chr(10)*2
        return Response(divider.join(parts))

    def _build_personal_report(self, person: str, label: str = None) -> str:
        display = label or person
        today = date.today()
        start = today.isoformat()
        end = (today + timedelta(days=1)).isoformat()
        date_str = today.strftime("%B %-d") if not _is_windows() else today.strftime("%B %d").lstrip("0").replace(" 0", " ")

        # Hurt data
        ouch_today = self.db.get_ouch_today(person)
        ouch_alltime = self.db.get_ouch_alltime(person)

        # Smile data
        smiles_today = self.db.get_smiles_today(person)
        smiles_alltime = self.db.get_smiles_alltime(person)

        lines = [
            f"\U0001f495 *HeartSync \u2014 {display}*",
            f"\U0001f4c5 {date_str}",
            "",
        ]

        # Hurt section
        hurt_count = len(ouch_today)
        lines.append(f"\U0001f494 *Hurt* ({hurt_count} today \u00b7 {ouch_alltime} all-time)")
        for entry in ouch_today:
            ts = datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M")
            msg = _truncate(entry.get("message") or "")
            lines.append(f"\u2022 {ts} \u2014 {msg}")

        lines.append("")

        # SmileJar section
        lines.append(f"\U0001f60a *SmileJar* ({smiles_today} today \u00b7 {smiles_alltime} all-time)")

        lines.append("")
        lines.append("\u2728 Keep sharing. Keep growing. \U0001f495")

        return "\n".join(lines)

    def _daily_reports_scheduled(self) -> list[Response]:
        """Generate one report per member for the 22:00 scheduled send."""
        reports = []
        for person, info in self._members.items():
            label = info.get("label", person) if isinstance(info, dict) else person
            text = self._build_personal_report(person, label)
            reports.append(Response(text))
        return reports

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        daily_time = self.config.get("daily_time", "22:00")
        dh, dm = map(int, daily_time.split(":"))

        return [
            ScheduledJob(
                job_id="heartsync_daily_reports",
                func=self._daily_reports_scheduled,
                trigger="cron",
                kwargs={"hour": dh, "minute": dm},
            ),
        ]


def _is_windows() -> bool:
    import sys
    return sys.platform == "win32"
