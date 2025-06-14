import yaml
from .logger import create_logger
from .translate import _t
from . import config
from pathlib import Path
from aiogram import types

logger = create_logger(__name__)
allowed_users = set()
banned_users = set()


def load_users(filename):
  try:
    with open(Path(__file__).parent / filename, 'r') as file:
      return set(yaml.safe_load(file) or [-1])
  except FileNotFoundError:
    return set([-1])


def check_user(user: types.User):
  if not allowed_users:
    allowed_users.update(load_users("allowed_users.yaml"))

  if user.id not in allowed_users:
    logger.fatal(f"user '{user.username}' is not allowed, id={user.id}")
    return True

  return False


def is_group_bot():
  return hasattr(config, "GROUP_ID")


def chat_to_other_bots():
  return hasattr(config, "CHAT_TO_OTHER_BOTS") and config.CHAT_TO_OTHER_BOTS


def check_group(chat_id):
  return chat_id != config.GROUP_ID


def is_user_not_allowed(message: types.Message):
  if is_group_bot():
    return check_group(message.chat.id)

  return check_user(message.from_user)


def is_user_banned(user_id):
  if not banned_users:
    banned_users.update(load_users("banned_users.yaml"))

  if user_id in banned_users:
    logger.debug(f"user is banned, id={user_id}")
    return True

  return False


async def has_access(message: types.Message):
  if message.from_user.is_bot:
    return False

  user_id = message.from_user.id

  if is_user_not_allowed(message):
    await message.answer(_t("bot.not_allowed", id=user_id))
    return False

  if is_user_banned(user_id):
    return False

  if is_group_bot() and message.reply_to_message is not None:
    if chat_to_other_bots():
      return message.reply_to_message.from_user.is_bot

    return (
        message.reply_to_message.from_user.id == message.bot.id  # replied to me (the bot)
        or message.reply_to_message.from_user.first_name == "Telegram"  # replied to postponed messages in the group
    )

  return True


async def access_middleware(handler, message: types.Message, data):
  logger.debug(f"middleware:{message}")

  if message.text is None and message.voice is None and message.document is None:
    logger.debug(f"blocked:message.text={message.text}")
    return

  if message.text == "/start" or await has_access(message):
    return await handler(message, data)
