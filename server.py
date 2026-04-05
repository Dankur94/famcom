"""FamCom — FastAPI server with WhatsApp bridge and message routing."""

import re
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request

logger = logging.getLogger("famcom")
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from registry import load_config, load_enabled_modules, route_message
from database import Database
from whatsapp import WhatsAppClient
from voice import VoiceProcessor
from modules.base import Message

# Keywords that hint at a bot command (DE + EN)
_COMMAND_HINTS = [
    "ausgabe", "ausgegeben", "bezahlt", "gekauft", "spent", "paid", "bought",
    "expense", "groceries", "taxi", "lunch", "dinner",
    "stunde", "stunden", "minuten", "cooking", "cleaning", "putzen", "kochen",
    "erinner", "remind", "reminder",
    "report", "weekly", "monthly", "woche", "monat",
    "loeschen", "löschen", "undo", "delete",
    "hilfe", "help",
    "ouch", "aua", "autsch",
    "pain", "schmerz",
    "goal", "maxim", "goals", "maxims",
    "asset", "assets",
]


def might_be_command(text: str) -> bool:
    """Cheap pre-filter: could this text be a bot command?"""
    t = text.lower().strip()
    if len(t) < 3:
        return False
    if t.startswith('$'):
        return True
    if re.search(r'\d', t):
        return True
    if t.startswith(('+', '-', '!')):
        return True
    return any(kw in t for kw in _COMMAND_HINTS)

# --- Import and register all modules ---
from registry import register_module
from modules.help.module import HelpModule
from modules.expense.module import ExpenseModule
from modules.time_log.module import TimeLogModule
from modules.delete.module import DeleteModule
from modules.reminders.module import RemindersModule
from modules.reports.module import ReportsModule
from modules.groceries.module import GroceriesModule
from modules.ai_query.module import AIQueryModule
from modules.ouch.module import OuchModule
from modules.pain.module import PainModule
from modules.goals.module import GoalsModule
from modules.assets.module import AssetsModule

register_module("help", HelpModule)
register_module("expense", ExpenseModule)
register_module("time_log", TimeLogModule)
register_module("ouch", OuchModule)
register_module("pain", PainModule)
register_module("goals", GoalsModule)
register_module("assets", AssetsModule)
register_module("delete", DeleteModule)
register_module("reminders", RemindersModule)
register_module("reports", ReportsModule)
register_module("groceries", GroceriesModule)
register_module("ai_query", AIQueryModule)

# --- Globals ---
config = load_config()
db = Database(
    path=config.get("database", {}).get("path", "famcom.db"),
)
wa = WhatsAppClient(config["whatsapp"])
modules = load_enabled_modules(config, db)
scheduler = AsyncIOScheduler()

# Pass members config to modules that support @person
members_config = config.get("members", {})
for mod in modules:
    if hasattr(mod, "set_members"):
        mod.set_members(members_config)

# Voice processor (Groq Whisper + DeepSeek) — prompt built from loaded modules
voice_config = config.get("voice", {})
voice_processor = VoiceProcessor(voice_config, modules, members_config) if voice_config.get("enabled") else None

TRACKING_MODULES = {"expense", "timelog", "thanks", "delete"}


def _send_scheduled(response):
    """Send a scheduled message (reminder, report) via the bridge."""
    if response:
        wa.send_message(response.text)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: register scheduled jobs from all modules
    for module in modules:
        for job in module.get_scheduled_jobs():
            original_func = job.func

            def make_sender(fn):
                def sender():
                    result = fn()
                    _send_scheduled(result)
                return sender

            scheduler.add_job(
                make_sender(original_func),
                trigger=job.trigger,
                id=job.job_id,
                **job.kwargs,
                replace_existing=True,
            )
    scheduler.start()
    print(f"FamCom started — {len(modules)} modules loaded")
    yield
    # Shutdown
    scheduler.shutdown()
    db.close()


app = FastAPI(lifespan=lifespan)


@app.post("/message")
async def handle_message(request: Request):
    """Receive message from WhatsApp bridge, route to modules."""
    body = await request.json()
    message = wa.parse_incoming(body)

    if not message:
        return {"reply": None}

    # Route through modules
    response = route_message(modules, message)

    if response:
        return {"reply": response.text}

    # AI Fallback: no regex match but text looks like a command
    if voice_processor and might_be_command(message.text):
        try:
            command = voice_processor.normalize(message.text)
            if command:
                normalized_msg = Message(
                    text=command,
                    sender=message.sender,
                    sender_phone=message.sender_phone,
                    timestamp=message.timestamp,
                )
                response = route_message(modules, normalized_msg)
                if response:
                    response.text = f"\U0001f4ac *Understood:* {message.text}\n\n" + response.text
                    return {"reply": response.text}
        except Exception:
            pass  # AI down → bot stays silent, regex still works

    # No match — bot stays silent (normal family conversation)
    return {"reply": None}


@app.post("/voice")
async def handle_voice(request: Request):
    """Receive voice note from bridge, transcribe, normalize, and route."""
    if not voice_processor:
        return {"reply": None}

    body = await request.json()

    # 1. Transcribe via Groq Whisper
    try:
        transcript = voice_processor.transcribe(body["audio_base64"])
        print(f"[VOICE] transcript: {transcript}")
    except Exception as e:
        print(f"[VOICE] transcribe error: {e}")
        return {"reply": f"\U0001f3a4 Voice error: {e}"}

    if not transcript:
        return {"reply": None}

    # 2. Normalize to bot command via DeepSeek
    try:
        command = voice_processor.normalize(transcript)
        print(f"[VOICE] normalize: '{transcript}' -> '{command}'")
    except Exception as e:
        print(f"[VOICE] normalize error: {e}")
        return {"reply": f"\U0001f3a4 *Voice:* {transcript}\n\n\u26a0\ufe0f Normalize error: {e}"}

    if not command:
        return {"reply": f"\U0001f3a4 *Heard:* {transcript}\n\n\u2753 Not recognized as a command. Type *help* for options."}

    # 3. Route as regular message
    message = Message(
        text=command,
        sender=body["sender"],
        sender_phone=body["sender_phone"],
        timestamp=body["timestamp"],
    )
    response = route_message(modules, message)

    if response:
        voice_header = f"\U0001f3a4 *Voice:* {transcript}"
        response.text = voice_header + "\n\n" + response.text
        return {"reply": response.text}

    return {"reply": f"\U0001f3a4 *Voice:* {transcript}\n\n\u2753 Command not recognized: {command}"}


@app.get("/health")
async def health():
    bridge_ok = wa.is_bridge_connected()
    return {
        "status": "running",
        "modules": len(modules),
        "whatsapp_bridge": "connected" if bridge_ok else "disconnected",
    }
