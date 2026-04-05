"""Base module contract — every module implements this interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    """Incoming WhatsApp message."""
    text: str
    sender: str          # WhatsApp display name
    sender_phone: str    # Phone number
    timestamp: str       # ISO format


@dataclass
class Response:
    """Outgoing WhatsApp response."""
    text: str


@dataclass
class ScheduledJob:
    """A scheduled task for APScheduler."""
    job_id: str
    func: callable
    trigger: str         # "cron" or "interval"
    kwargs: dict         # trigger-specific args (hour, minute, seconds, etc.)


class BaseModule(ABC):
    """Contract for all modules. Every module must implement these 3 methods."""

    # Override in subclass to enable AI voice/text recognition.
    # Format: {"command": "format string", "examples": [("input", "output"), ...]}
    VOICE_INFO: dict | None = None

    def __init__(self, config: dict, db=None):
        self.config = config
        self.db = db

    @abstractmethod
    def can_handle(self, message: Message) -> bool:
        """Return True if this module should process the message."""
        pass

    @abstractmethod
    def handle(self, message: Message) -> Response | None:
        """Process the message and return a response (or None for silence)."""
        pass

    @abstractmethod
    def get_scheduled_jobs(self) -> list[ScheduledJob]:
        """Return list of scheduled jobs this module needs."""
        pass
