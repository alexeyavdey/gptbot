from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from .handlers import router
from . import env
import signal
import sys

async def main():
  bot = Bot(
      token=env.BOT_TOKEN,
      default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
  )

  dp = Dispatcher()
  dp.include_router(router)

  # Инициализируем систему уведомлений
  try:
    from .notifications import init_notifications, stop_notifications
    init_notifications(bot)
    
    # Обработчик сигналов для корректного завершения
    def signal_handler(sig, frame):
        print('\nЗавершение работы...')
        stop_notifications()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 Бот запущен с системой уведомлений")
  except Exception as e:
    print(f"⚠️ Система уведомлений не инициализирована: {e}")
  
  try:
    await dp.start_polling(bot)
  finally:
    # Останавливаем уведомления при завершении
    try:
      from .notifications import stop_notifications
      stop_notifications()
    except:
      pass
