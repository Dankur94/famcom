"""Module registry — loads enabled modules from config.yaml."""

import yaml
from modules.base import BaseModule, Message, Response


# Map config names to module classes (populated by register_modules)
MODULE_MAP: dict[str, type[BaseModule]] = {}


def register_module(name: str, cls: type[BaseModule]):
    """Register a module class under a config name."""
    MODULE_MAP[name] = cls


def load_config(path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(path, "r") as f:
        return yaml.safe_load(f)


def load_enabled_modules(config: dict, db=None) -> list[BaseModule]:
    """Instantiate all enabled modules from config."""
    modules = []
    module_configs = config.get("modules", {})

    for name, mod_config in module_configs.items():
        if not isinstance(mod_config, dict):
            continue
        if not mod_config.get("enabled", False):
            continue
        if name not in MODULE_MAP:
            print(f"Warning: Module '{name}' enabled but not registered")
            continue

        cls = MODULE_MAP[name]
        module = cls(config=mod_config, db=db)
        modules.append(module)
        print(f"Loaded module: {name}")

    return modules


def route_message(modules: list[BaseModule], message: Message) -> Response | None:
    """Route a message to the first module that can handle it.
    Supports multi-line messages — each line is routed independently.
    Returns None if no module matches (bot stays silent)."""
    lines = [l.strip() for l in message.text.strip().splitlines() if l.strip()]

    if len(lines) <= 1:
        for module in modules:
            if module.can_handle(message):
                return module.handle(message)
        return None

    responses = []
    for line in lines:
        line_msg = Message(text=line, sender=message.sender, sender_phone=message.sender_phone, timestamp=message.timestamp)
        for module in modules:
            if module.can_handle(line_msg):
                resp = module.handle(line_msg)
                if resp:
                    responses.append(resp.text)
                break

    if responses:
        return Response("\n".join(responses))
    return None
