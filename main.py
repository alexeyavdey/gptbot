from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from .handlers import router
from . import env


async def main():
  bot = Bot(
      token=env.BOT_TOKEN,
      default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
  )

  dp = Dispatcher()
  dp.include_router(router)

  await dp.start_polling(bot)
