"""Help module — shows all available commands."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

HELP_TEXT = """\
*HeartSync* \U0001f495

\U0001f494 *Hurt*
  `hurt du hast mich ignoriert` \u2014 log what happened
  `ouch das war gemein` \u2014 same thing
  `aua`, `autsch`, `verletzt` \u2014 also work

\U0001f60a *SmileJar*
  `smile` \u2014 +1 moment of joy
  `smile date night was amazing` \u2014 with note
  `laugh`, `haha`, `lol`, `gelacht` \u2014 also work

\U0001f4ca *Report*
  `report` / `today` / `status` \u2014 your personal daily report
  \u2022 22:00 daily \u2014 automatic report for each person

\U0001f5d1 *Delete*
  `undo` \u2014 delete your last entry
  `delete hurt 14:30` \u2014 delete hurt at time
  `delete smile 09:00` \u2014 delete smile at time

\u2753 `help` \u2014 this message"""


class HelpModule(BaseModule):
    VOICE_INFO = {
        "command": "help",
        "examples": [
            ("what can you do", "help"),
            ("show me the commands", "help"),
            ("hilfe", "help"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        return t in ("help", "?", "commands", "hilfe")

    def handle(self, message: Message) -> Response:
        return Response(HELP_TEXT)

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        return []
