"""WhatsApp integration via Baileys bridge."""

import httpx
from modules.base import Message

# The Node.js bridge runs on this port
BRIDGE_URL = "http://localhost:3002"


class WhatsAppClient:
    def __init__(self, config: dict):
        self.bridge_url = config.get("bridge_url", BRIDGE_URL)

    def send_message(self, text: str):
        """Send a message to the group via the Node.js bridge."""
        response = httpx.post(
            f"{self.bridge_url}/send",
            json={"text": text},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    def parse_incoming(self, body: dict) -> Message | None:
        """Parse incoming message from the bridge into a Message object."""
        try:
            return Message(
                text=body["text"],
                sender=body["sender"],
                sender_phone=body["sender_phone"],
                timestamp=body["timestamp"],
            )
        except (KeyError, TypeError):
            return None

    def is_bridge_connected(self) -> bool:
        """Check if the WhatsApp bridge is running."""
        try:
            response = httpx.get(f"{self.bridge_url}/health", timeout=5.0)
            return response.json().get("status") == "connected"
        except Exception:
            return False
