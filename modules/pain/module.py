"""Pain module — log personal pain/struggles (not caused by family)."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

_PAIN_PATTERN = re.compile(
    r'^(?:pain|schmerz|schmerzen)\s*(.*)',
    re.IGNORECASE | re.DOTALL
)


class PainModule(BaseModule):
    VOICE_INFO = {
        "command": "pain [optional message]",
        "examples": [
            ("pain kopfschmerzen seit heute morgen", "pain kopfschmerzen seit heute morgen"),
            ("schmerzen im ruecken", "schmerzen im ruecken"),
            ("pain", "pain"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        return bool(_PAIN_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _PAIN_PATTERN.match(message.text.strip())
        if not match:
            return None

        text = match.group(1).strip()

        entry = self.db.add_pain(
            logged_by=message.sender,
            message=text or None,
        )

        if text:
            return Response("\U0001fa79 Noted. Get well soon!")
        else:
            return Response("\U0001fa79 Noted. Hope you feel better soon.")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
