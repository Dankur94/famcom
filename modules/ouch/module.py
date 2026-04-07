"""Hurt module — log when something said was hurtful."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

_HURT_PATTERN = re.compile(
    r'^(?:ouch|aua|autsch|hurt|verletzt)\s*(.*)',
    re.IGNORECASE | re.DOTALL
)


class OuchModule(BaseModule):
    VOICE_INFO = {
        "command": "hurt [message describing what happened]",
        "examples": [
            ("hurt du hast mich ignoriert", "hurt du hast mich ignoriert"),
            ("ouch das war gemein", "ouch das war gemein"),
            ("aua du hast mich angeschrien", "aua du hast mich angeschrien"),
            ("verletzt weil du nicht zugehoert hast", "verletzt weil du nicht zugehoert hast"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        return bool(_HURT_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _HURT_PATTERN.match(message.text.strip())
        if not match:
            return None

        text = match.group(1).strip()

        if not text:
            return Response("\U0001f494 Please describe what happened.\nExample: `hurt du hast mich ignoriert`")

        self.db.add_ouch(
            logged_by=message.sender,
            message=text,
        )

        today = len(self.db.get_ouch_today(message.sender))
        alltime = self.db.get_ouch_alltime(message.sender)

        return Response(f"\U0001f494 Logged. Today: {today} | All-time: {alltime}")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
