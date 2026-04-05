"""Reminders module — DB-backed reminders with APScheduler polling."""

import re
from datetime import datetime, timedelta, date
from modules.base import BaseModule, Message, Response, ScheduledJob

# Patterns:
# remind 15:00 call doctor
# remind me in 2h pick up laundry
# remind me in 30min check oven
# remind tomorrow 09:00 buy milk
# reminders — list upcoming
_TIME_PATTERN = re.compile(
    r'^remind(?:\s+me)?\s+(\d{1,2}:\d{2})\s+(.+)\s*$',
    re.IGNORECASE
)
_DELTA_PATTERN = re.compile(
    r'^remind(?:\s+me)?\s+in\s+(\d+(?:\.\d+)?)\s*(h|hr|hrs|hours?|min|mins|minutes?)\s+(.+)\s*$',
    re.IGNORECASE
)
_TOMORROW_PATTERN = re.compile(
    r'^remind(?:\s+me)?\s+tomorrow\s+(\d{1,2}:\d{2})\s+(.+)\s*$',
    re.IGNORECASE
)


class RemindersModule(BaseModule):
    VOICE_INFO = {
        "command": "remind HH:MM MESSAGE or remind me in Xh MESSAGE",
        "examples": [
            ("remind me at 3pm to call the doctor", "remind 15:00 call doctor"),
            ("erinner mich in 2 stunden wasche abholen", "remind me in 2h pick up laundry"),
            ("set a reminder for tomorrow 9am buy milk", "remind tomorrow 09:00 buy milk"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        if t == "reminders":
            return True
        return bool(
            _TIME_PATTERN.match(message.text.strip())
            or _DELTA_PATTERN.match(message.text.strip())
            or _TOMORROW_PATTERN.match(message.text.strip())
        )

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip()

        if t.lower() == "reminders":
            return self._list_upcoming(message.sender)

        # Try each pattern
        match = _TIME_PATTERN.match(t)
        if match:
            time_str = match.group(1)
            msg_text = match.group(2).strip()
            h, m = map(int, time_str.split(":"))
            remind_at = datetime.combine(date.today(), datetime.min.time()).replace(hour=h, minute=m)
            # If time already passed today, schedule for tomorrow
            if remind_at < datetime.now():
                remind_at += timedelta(days=1)
            return self._create_reminder(message.sender, remind_at, msg_text)

        match = _DELTA_PATTERN.match(t)
        if match:
            amount = float(match.group(1))
            unit = match.group(2).lower()
            msg_text = match.group(3).strip()
            if unit.startswith(("h",)):
                delta = timedelta(hours=amount)
            else:
                delta = timedelta(minutes=amount)
            remind_at = datetime.now() + delta
            return self._create_reminder(message.sender, remind_at, msg_text)

        match = _TOMORROW_PATTERN.match(t)
        if match:
            time_str = match.group(1)
            msg_text = match.group(2).strip()
            h, m = map(int, time_str.split(":"))
            tomorrow = date.today() + timedelta(days=1)
            remind_at = datetime.combine(tomorrow, datetime.min.time()).replace(hour=h, minute=m)
            return self._create_reminder(message.sender, remind_at, msg_text)

        return None

    def _create_reminder(self, creator: str, remind_at: datetime, message: str) -> Response:
        result = self.db.add_reminder(
            created_by=creator,
            remind_at=remind_at.isoformat(),
            message=message,
        )
        time_display = remind_at.strftime("%H:%M")
        date_display = remind_at.strftime("%d.%m")
        return Response(f"⏰ Reminder set for *{date_display} {time_display}*:\n{message}")

    def _list_upcoming(self, sender: str) -> Response:
        upcoming = self.db.get_upcoming_reminders()
        if not upcoming:
            return Response("No upcoming reminders.")

        lines = ["⏰ *Upcoming Reminders:*"]
        for r in upcoming[:10]:
            t = datetime.fromisoformat(r["remind_at"]).strftime("%d.%m %H:%M")
            lines.append(f"  {t} — {r['message']} (by {r['created_by']})")
        return Response("\n".join(lines))

    def _check_and_send_reminders(self) -> Response | None:
        """Called by scheduler every minute. Sends due reminders."""
        pending = self.db.get_pending_reminders()
        if not pending:
            return None

        lines = []
        for r in pending:
            lines.append(f"⏰ *Reminder* (from {r['created_by']}):\n{r['message']}")
            self.db.mark_reminder_sent(r["id"])

        if lines:
            return Response("\n\n".join(lines))
        return None

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return [
            ScheduledJob(
                job_id="famcom_reminder_check",
                func=self._check_and_send_reminders,
                trigger="interval",
                kwargs={"seconds": 60},
            )
        ]
