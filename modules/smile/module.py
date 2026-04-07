"""SmileJar module — count moments of joy."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

_SMILE_PATTERN = re.compile(
    r'^(?:smile|smiled|laugh|laughed|lol|haha|joy|smilejar|gelacht)\s*(.*)',
    re.IGNORECASE | re.DOTALL
)


class SmileModule(BaseModule):
    VOICE_INFO = {
        "command": "smile [optional message]",
        "examples": [
            ("smile date night was amazing", "smile date night was amazing"),
            ("haha das war lustig", "haha das war lustig"),
            ("gelacht beim Abendessen", "gelacht beim Abendessen"),
            ("smile", "smile"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        return bool(_SMILE_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _SMILE_PATTERN.match(message.text.strip())
        if not match:
            return None

        msg = match.group(1).strip() or None

        self.db.add_smile(
            logged_by=message.sender,
            message=msg,
        )

        today = self.db.get_smiles_today(message.sender)
        alltime = self.db.get_smiles_alltime(message.sender)

        return Response(f"\U0001f60a +1! \U0001fad9 Today: {today} | All-time: {alltime}")

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
