"""Voice processing — Groq Whisper STT + DeepSeek command normalization."""

import io
import base64
from openai import OpenAI

_PROMPT_HEADER = """\
You extract HeartSync bot commands from voice transcripts.
HeartSync tracks feelings — hurt moments and smiles/joy between partners.
Return ONLY the command, nothing else. If the transcript is not a bot command, return "NONE"."""

_PROMPT_FOOTER = """
- "hallo wie gehts euch" → NONE
- "good morning everyone" → NONE"""


def build_normalize_prompt(modules: list, members: dict = None) -> str:
    """Build the normalize prompt dynamically from loaded modules."""
    commands = []
    examples = []

    for mod in modules:
        info = getattr(mod, "VOICE_INFO", None)
        if not info:
            continue
        name = type(mod).__name__.replace("Module", "")
        commands.append(f"- {name}: {info['command']}")
        for inp, out in info.get("examples", []):
            examples.append(f'- "{inp}" → {out}')

    parts = [_PROMPT_HEADER, "\nAvailable commands:"]
    parts.extend(commands)

    # Add member aliases so AI knows how to resolve names
    if members:
        parts.append("\nFamily members (use @name in commands):")
        for name, info in members.items():
            aliases = ", ".join(info.get("aliases", []))
            parts.append(f'- {name}: aliases = {aliases} → use @{name}')
        parts.append('When someone mentions a family member, add @NAME to the command.')

    if examples:
        parts.append("\nExamples:")
        parts.extend(examples)
    parts.append(_PROMPT_FOOTER)

    return "\n".join(parts)


class VoiceProcessor:
    def __init__(self, config: dict, modules: list | None = None, members: dict = None):
        self.groq_client = OpenAI(
            api_key=config.get("groq_api_key", ""),
            base_url="https://api.groq.com/openai/v1",
        )
        self.deepseek_client = OpenAI(
            api_key=config.get("deepseek_api_key", ""),
            base_url=config.get("deepseek_base_url", "https://api.deepseek.com"),
        )
        self.deepseek_model = config.get("deepseek_model", "deepseek-chat")
        self._members = members or {}
        self._prompt = build_normalize_prompt(modules, self._members) if modules else _PROMPT_HEADER

    def set_modules(self, modules: list):
        """Update the normalize prompt with current modules."""
        self._prompt = build_normalize_prompt(modules, self._members)

    def transcribe(self, audio_base64: str) -> str:
        """Groq Whisper: base64 .ogg → text transcript."""
        audio_bytes = base64.b64decode(audio_base64)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "voice.ogg"

        response = self.groq_client.audio.transcriptions.create(
            model="whisper-large-v3-turbo",
            file=audio_file,
            language="de",
        )
        return response.text.strip()

    def normalize(self, transcript: str) -> str | None:
        """DeepSeek: transcript → bot command (or None if not a command)."""
        response = self.deepseek_client.chat.completions.create(
            model=self.deepseek_model,
            messages=[
                {"role": "system", "content": self._prompt},
                {"role": "user", "content": transcript},
            ],
            max_tokens=100,
            temperature=0,
        )
        result = response.choices[0].message.content.strip()
        if result.upper() in ("NONE", "NULL", "SKIP", ""):
            return None
        return result
