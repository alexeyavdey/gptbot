from aiogram import types
from .client import client
from .logger import create_logger

logger = create_logger(__name__)


async def decode_voice(message: types.Message) -> str | None:
  try:
    file = await message.bot.download(message.voice.file_id)
    file.name = "voice.ogg"
    response = await client.audio.transcriptions.create(
        model="whisper-1",
        file=file
    )
    return response.text.strip()
  except Exception as error:
    logger.error(f"decode_voice:{error}")
    return None
