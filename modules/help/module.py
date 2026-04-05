"""Help module — shows all available commands."""

import re
from modules.base import BaseModule, Message, Response, ScheduledJob

HELP_TEXT = """\
*FamCom — Family Contributions*

💰 *Expenses (HKD)*
  `$50 groceries` — log expense
  `expense 150 taxi` — log expense
  `$30 lunch @babe` — for someone else
  `$30 lunch 14:30` — with time

⏱ *Time Investments*
  `2h cooking` — log time
  `30min cleaning @opa` — for someone else
  `1.5h gardening 09:00` — with time

🛒 *Groceries*
  `bought milk, eggs, bread` — log items
  `bought @opa milk, bread` — for someone
  `groceries` — show today's list

📊 *Reports*
  `report` / `weekly` — this week
  `monthly` — this month
  `today` — today's entries
  `total` — all-time family ledger

⏰ *Reminders*
  `remind 15:00 call doctor`
  `remind me in 2h pick up laundry`
  `reminders` — show upcoming

💔 *Ouch*
  `ouch` — someone in the family hurt you
  `ouch you yelled at me` — with context
  `ouch @babe that was mean` — about someone

🩹 *Pain*
  `pain` — personal pain/struggle (not family)
  `pain headache since this morning`
  `pain back pain`

🎯 *Goals*
  `goal save 10k this year` — add a goal
  `goals` — list your goals
  `delete goal 2` — remove goal #2

✨ *Maxims*
  `maxim always be honest` — add a life maxim
  `maxims` — list your maxims
  `delete maxim 1` — remove maxim #1

🗑 *Delete*
  `undo` — delete last entry
  `delete expense 14:30`
  `delete time 09:00`

🤖 *AI Query*
  `!q how much did we spend this week`

❓ `help` — this message"""


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
