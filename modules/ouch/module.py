"""Ouch module — log when something said was hurtful."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

_OUCH_PATTERN = re.compile(
    r'^(?:ouch|aua|autsch)\s*(.*)',
    re.IGNORECASE | re.DOTALL
)


class OuchModule(BaseModule):
    VOICE_INFO = {
        "command": "ouch [optional message]",
        "examples": [
            ("ouch das war gemein", "ouch das war gemein"),
            ("aua du hast mich angeschrien", "aua du hast mich angeschrien"),
            ("ouch", "ouch"),
        ],
    }

    def __init__(self, config: dict, db=None):
        super().__init__(config, db)
        self._members = {}

    def set_members(self, members_config: dict):
        self._members = members_config

    def _resolve_member(self, text: str) -> tuple[str | None, str]:
        """Extract @person from text. Returns (resolved_name, remaining_text)."""
        match = re.match(r'^@(\w+)\s*(.*)', text, re.DOTALL)
        if not match:
            return None, text

        alias = match.group(1).lower()
        remaining = match.group(2).strip()

        for name, info in self._members.items():
            aliases = [a.lower() for a in info.get("aliases", [])]
            if alias == name.lower() or alias in aliases:
                return name, remaining

        return None, text

    def can_handle(self, message: Message) -> bool:
        return bool(_OUCH_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _OUCH_PATTERN.match(message.text.strip())
        if not match:
            return None

        rest = match.group(1).strip()

        # Check for @person
        about_user, text = self._resolve_member(rest)

        entry = self.db.add_ouch(
            logged_by=message.sender,
            about_user=about_user,
            message=text or None,
        )

        parts = ["\U0001f494 Noted."]
        if text:
            parts.append("Thanks for sharing.")
        else:
            parts.append("Thanks for speaking up.")

        return Response(" ".join(parts))

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
