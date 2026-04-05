"""Reports module — weekly/monthly/all-time per-person breakdown + daily 8am summary."""

import re
from datetime import datetime, date, timedelta
from modules.base import BaseModule, Message, Response, ScheduledJob


def _fmt_money(amount: float) -> str:
    return f"${amount:,.0f}"


def _fmt_time(minutes: int) -> str:
    if minutes >= 60:
        h = minutes / 60
        return f"{h:.1f}h"
    return f"{minutes}min"


class ReportsModule(BaseModule):
    VOICE_INFO = {
        "command": "report or weekly or monthly or today or total",
        "examples": [
            ("show me the weekly report", "weekly"),
            ("wie sieht es diese woche aus", "report"),
            ("monthly summary", "monthly"),
            ("was war heute", "today"),
            ("gesamtuebersicht", "total"),
            ("show me everything", "total"),
            ("wer hat insgesamt was beigetragen", "total"),
        ],
    }

    def can_handle(self, message: Message) -> bool:
        t = message.text.strip().lower()
        return t in ("report", "weekly", "monthly", "today", "status",
                      "summary", "total", "all", "gesamt", "ledger")

    def handle(self, message: Message) -> Response | None:
        t = message.text.strip().lower()
        if t == "monthly":
            return Response(self._monthly_report())
        elif t == "today":
            return Response(self._today_report())
        elif t in ("total", "all", "gesamt", "ledger"):
            return Response(self._total_report())
        else:
            return Response(self._weekly_report())

    def _today_report(self) -> str:
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        return self._build_report("Today", today, tomorrow)

    def _weekly_report(self) -> str:
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=7)
        return self._build_report("This Week", start.isoformat(), end.isoformat())

    def _monthly_report(self) -> str:
        today = date.today()
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1)
        else:
            end = today.replace(month=today.month + 1, day=1)
        return self._build_report("This Month", start.isoformat(), end.isoformat())

    def _total_report(self) -> str:
        """All-time family ledger."""
        expenses_by_person = self.db.get_all_expenses_by_person()
        time_by_person = self.db.get_all_time_by_person()
        thanks_by_person = self.db.get_all_thanks_by_person()
        ouch_by_person = self.db.get_all_ouch_by_person()
        pain_by_person = self.db.get_all_pain_by_person()

        all_people = set()
        all_people.update(expenses_by_person.keys())
        all_people.update(time_by_person.keys())
        all_people.update(thanks_by_person.keys())
        all_people.update(ouch_by_person.keys())
        all_people.update(pain_by_person.keys())

        if not all_people:
            return "📒 *Familie Kurth — Ledger*\n\nNo entries yet. Start logging with `$50 groceries` or `2h cooking`."

        first_date = self.db.get_first_entry_date()
        since = ""
        if first_date:
            since = f" (since {datetime.fromisoformat(first_date).strftime('%d.%m.%Y')})"

        lines = [f"📒 *Familie Kurth — Ledger*{since}", ""]

        # Grand totals
        total_expenses = sum(d["total"] for d in expenses_by_person.values())
        total_time = sum(d["total_min"] for d in time_by_person.values())
        total_thanks = sum(d["count"] for d in thanks_by_person.values())
        total_ouch = sum(d["count"] for d in ouch_by_person.values())
        total_pain = sum(d["count"] for d in pain_by_person.values())

        lines.append(f"💰 Total spent: {_fmt_money(total_expenses)}")
        lines.append(f"⏱ Total time invested: {_fmt_time(total_time)}")
        lines.append(f"🙏 Total kudos: {total_thanks}")
        if total_ouch:
            lines.append(f"💔 Ouch moments: {total_ouch}")
        if total_pain:
            lines.append(f"🩹 Pain entries: {total_pain}")
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━")

        # Per-person breakdown — sorted by total expenses descending
        people_sorted = sorted(all_people, key=lambda p: expenses_by_person.get(p, {}).get("total", 0), reverse=True)

        for person in people_sorted:
            lines.append("")
            person_total = expenses_by_person.get(person, {}).get("total", 0)
            pct = (person_total / total_expenses * 100) if total_expenses > 0 else 0

            lines.append(f"👤 *{person}*")

            if person in expenses_by_person:
                d = expenses_by_person[person]
                lines.append(f"  💰 {_fmt_money(d['total'])} ({pct:.0f}% of total, {d['count']}x)")
                cats = sorted(d["categories"].items(), key=lambda x: -x[1])[:5]
                for cat, amt in cats:
                    lines.append(f"    {cat}: {_fmt_money(amt)}")

            if person in time_by_person:
                d = time_by_person[person]
                lines.append(f"  ⏱ {_fmt_time(d['total_min'])} ({d['count']}x)")
                cats = sorted(d["categories"].items(), key=lambda x: -x[1])[:5]
                for cat, mins in cats:
                    lines.append(f"    {cat}: {_fmt_time(mins)}")

            if person in thanks_by_person:
                d = thanks_by_person[person]
                lines.append(f"  🙏 {d['count']} kudos received")

            if person in ouch_by_person:
                d = ouch_by_person[person]
                lines.append(f"  💔 {d['count']} ouch moment{'s' if d['count'] != 1 else ''}")

            if person in pain_by_person:
                d = pain_by_person[person]
                lines.append(f"  🩹 {d['count']} pain entr{'ies' if d['count'] != 1 else 'y'}")

        return "\n".join(lines)

    def _build_report(self, title: str, start: str, end: str) -> str:
        expenses_by_person = self.db.get_expenses_by_person(start, end)
        time_by_person = self.db.get_time_by_person(start, end)
        thanks_by_person = self.db.get_thanks_by_person(start, end)
        ouch_by_person = self.db.get_ouch_by_person(start, end)
        pain_by_person = self.db.get_pain_by_person(start, end)

        all_people = set()
        all_people.update(expenses_by_person.keys())
        all_people.update(time_by_person.keys())
        all_people.update(thanks_by_person.keys())
        all_people.update(ouch_by_person.keys())
        all_people.update(pain_by_person.keys())

        if not all_people:
            return f"📊 *{title}*\n\nNo entries yet."

        lines = [f"📊 *{title}*", ""]

        total_expenses = sum(d["total"] for d in expenses_by_person.values())
        total_time = sum(d["total_min"] for d in time_by_person.values())
        total_thanks = sum(d["count"] for d in thanks_by_person.values())
        total_ouch = sum(d["count"] for d in ouch_by_person.values())
        total_pain = sum(d["count"] for d in pain_by_person.values())

        lines.append(f"💰 Total expenses: {_fmt_money(total_expenses)}")
        lines.append(f"⏱ Total time: {_fmt_time(total_time)}")
        lines.append(f"🙏 Total thanks: {total_thanks}")
        if total_ouch:
            lines.append(f"💔 Ouch moments: {total_ouch}")
        if total_pain:
            lines.append(f"🩹 Pain entries: {total_pain}")
        lines.append("")

        for person in sorted(all_people):
            lines.append(f"*{person}:*")

            if person in expenses_by_person:
                d = expenses_by_person[person]
                lines.append(f"  💰 {_fmt_money(d['total'])} ({d['count']}x)")
                for cat, amt in sorted(d["categories"].items(), key=lambda x: -x[1]):
                    lines.append(f"    {cat}: {_fmt_money(amt)}")

            if person in time_by_person:
                d = time_by_person[person]
                lines.append(f"  ⏱ {_fmt_time(d['total_min'])} ({d['count']}x)")
                for cat, mins in sorted(d["categories"].items(), key=lambda x: -x[1]):
                    lines.append(f"    {cat}: {_fmt_time(mins)}")

            if person in thanks_by_person:
                d = thanks_by_person[person]
                lines.append(f"  🙏 {d['count']} kudos received")

            if person in ouch_by_person:
                d = ouch_by_person[person]
                lines.append(f"  💔 {d['count']} ouch moment{'s' if d['count'] != 1 else ''}")

            if person in pain_by_person:
                d = pain_by_person[person]
                lines.append(f"  🩹 {d['count']} pain entr{'ies' if d['count'] != 1 else 'y'}")

            lines.append("")

        return "\n".join(lines).strip()

    # --- Daily 8am Summary (yesterday per person) ---

    def _daily_summary(self) -> str:
        """Yesterday's per-person summary: contributions, ouch, pain."""
        yesterday = date.today() - timedelta(days=1)
        start = yesterday.isoformat()
        end = date.today().isoformat()
        day_str = yesterday.strftime("%d.%m.%Y")

        expenses_by_person = self.db.get_expenses_by_person(start, end)
        time_by_person = self.db.get_time_by_person(start, end)
        thanks_by_person = self.db.get_thanks_by_person(start, end)
        ouch_by_person = self.db.get_ouch_by_person(start, end)
        pain_by_person = self.db.get_pain_by_person(start, end)

        all_people = set()
        all_people.update(expenses_by_person.keys())
        all_people.update(time_by_person.keys())
        all_people.update(thanks_by_person.keys())
        all_people.update(ouch_by_person.keys())
        all_people.update(pain_by_person.keys())

        if not all_people:
            return f"☀️ *Guten Morgen — {day_str}*\n\nGestern keine Eintraege."

        lines = [f"☀️ *Guten Morgen — {day_str}*", ""]

        for person in sorted(all_people):
            lines.append(f"👤 *{person}*")

            if person in expenses_by_person:
                d = expenses_by_person[person]
                lines.append(f"  💰 {_fmt_money(d['total'])} ({d['count']}x)")

            if person in time_by_person:
                d = time_by_person[person]
                lines.append(f"  ⏱ {_fmt_time(d['total_min'])} ({d['count']}x)")

            if person in thanks_by_person:
                d = thanks_by_person[person]
                lines.append(f"  🙏 {d['count']} kudos")

            if person in ouch_by_person:
                d = ouch_by_person[person]
                lines.append(f"  💔 {d['count']} ouch")

            if person in pain_by_person:
                d = pain_by_person[person]
                lines.append(f"  🩹 {d['count']} pain")

            lines.append("")

        return "\n".join(lines).strip()

    def _daily_summary_scheduled(self) -> Response | None:
        return Response(self._daily_summary())

    def _weekly_report_scheduled(self) -> Response | None:
        return Response(self._weekly_report())

    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        day = self.config.get("weekly_day", "sun")
        time_str = self.config.get("weekly_time", "20:00")
        h, m = map(int, time_str.split(":"))

        daily_time = self.config.get("daily_time", "08:00")
        dh, dm = map(int, daily_time.split(":"))

        return [
            ScheduledJob(
                job_id="famcom_weekly_report",
                func=self._weekly_report_scheduled,
                trigger="cron",
                kwargs={"day_of_week": day, "hour": h, "minute": m},
            ),
            ScheduledJob(
                job_id="famcom_daily_summary",
                func=self._daily_summary_scheduled,
                trigger="cron",
                kwargs={"hour": dh, "minute": dm},
            ),
        ]
