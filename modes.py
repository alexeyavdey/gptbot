import yaml
from pathlib import Path
from aiogram import types
from .logger import create_logger

logger = create_logger(__name__)

storage = Path(__file__).parent / "modes.yaml"
user_modes = {}


def load():
    try:
        with open(storage, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}


def save():
    with open(storage, 'w') as file:
        yaml.dump(user_modes, file, allow_unicode=True)


async def get_mode(user_id=None, new_mode=None):
    if not user_modes:
        user_modes.update(load())

    if user_id is None:
        return user_modes

    if new_mode:
        user_modes[user_id] = new_mode
        save()
        return new_mode

    return user_modes.get(user_id, "assistant")


def mode_filter(message: types.Message):
    return message.text in ["assistant", "gpt-4.1", "o4-mini"]
