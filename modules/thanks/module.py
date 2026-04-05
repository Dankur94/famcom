"""Thanks module — track kudos and appreciation."""

import re
from datetime import datetime
from modules.base import BaseModule, Message, Response, ScheduledJob

# Pattern: thanks papa for shopping | danke mama for cooking
_THANKS_PATTERN = re.compile(
    r'^(?:thanks|thank you|danke|thx)\s+(\w+)\s+(?:for|fuer|für)\s+(.+)\s*$',
    re.IGNORECASE
)


class ThanksModule(BaseModule):
    VOICE_INFO = {
        "command": "thanks NAME for REASON",
        "examples": [
            ("thanks papa for shopping", "thanks papa for shopping"),
            ("danke mama fuer kochen", "danke mama for cooking"),
            ("thank you dad for driving", "thanks dad for driving"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        return bool(_THANKS_PATTERN.match(message.text.strip()))

    def handle(self, message: Message) -> Response | None:
        match = _THANKS_PATTERN.match(message.text.strip())
        if not match:
            return None

        to_user = match.group(1).strip()
        reason = match.group(2).strip()

        result = self.db.add_thanks(
            from_user=message.sender,
            to_user=to_user,
            message=reason,
        )

        return Response(
            f"🙏 *{message.sender}* thanks *{to_user}* for {reason}"
        )

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
