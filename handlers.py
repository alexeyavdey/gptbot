from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command
from . import env
from .actions import change_assistant, handle_response, change_mode, clear_history
from .client import get_thread, get_assistant, asst_filter
from .logger import create_logger
from .translate import _t
from .helpers import escape_markdown
from .users import access_middleware
from .modes import get_mode, mode_filter
from .voice import decode_voice
from aiogram.types import WebAppInfo
import httpx
import asyncio

logger = create_logger(__name__)
router = Router()
router.message.middleware(access_middleware)


async def start_vapi_call(user: types.User) -> str:
  if not env.VAPI_API_KEY or not env.VAPI_ASSISTANT_ID:
    return "VAPI credentials not configured"

  headers = {
      "Authorization": f"Bearer {env.VAPI_API_KEY}",
      "Content-Type": "application/json",
  }
  payload = {
      "assistantId": env.VAPI_ASSISTANT_ID,
      "metadata": {
          "telegram_id": user.id,
          "username": user.username,
      },
  }
  try:
    async with httpx.AsyncClient() as client:
      resp = await client.post(
          "https://api.vapi.ai/v1/calls",
          headers=headers,
          json=payload,
      )
      resp.raise_for_status()
      data = resp.json()
      call_id = data.get("id")
      summary = data.get("summary")
      if not summary and call_id:
        for _ in range(20):
          await asyncio.sleep(3)
          r = await client.get(
              f"https://api.vapi.ai/v1/calls/{call_id}",
              headers=headers,
          )
          r.raise_for_status()
          d = r.json()
          if d.get("summary"):
            summary = d["summary"]
            break
      return summary or ""
  except Exception as exc:
    logger.error(f"start_vapi_call:error:{exc}")
    return "Error contacting VAPI API"


@router.message(CommandStart())
async def on_start(message: types.Message) -> None:
  logger.info(f"on_start:{message.from_user.username}:{message.from_user.id}")
  await message.answer(_t("bot.welcome", name=escape_markdown(message.from_user.full_name), id=message.from_user.id))


@router.message(Command("new"))
async def on_new(message: types.Message) -> None:
  await message.answer(_t("bot.new_chat"))
  thread = await get_thread(message.from_user.id, new_thread=True)
  logger.debug(f"on_new:{thread}")
  mode = await get_mode(message.from_user.id)
  if mode != "assistant":
    clear_history(message.from_user.id)


@router.message(Command("tutor"))
async def on_tutor(message: types.Message) -> None:
  tutors = await get_assistant()
  logger.info(f"on_tutor:{[id for id, _ in tutors.items()]}")
  await message.answer(
      _t("bot.new_tutor", tutors="\n".join([f"`{id}`: {info['desc']}" for id, info in tutors.items()])),
      reply_markup=types.ReplyKeyboardMarkup(
          keyboard=[[types.KeyboardButton(text=id) for id, _ in tutors.items()]],
          resize_keyboard=True
      )
  )


@router.message(Command("mode"))
async def on_mode(message: types.Message) -> None:
  modes = ["assistant", "gpt-4.1"]
  await message.answer(
      _t("bot.new_mode"),
      reply_markup=types.ReplyKeyboardMarkup(
          keyboard=[[types.KeyboardButton(text=mode) for mode in modes]],
          resize_keyboard=True
      )
  )


@router.message(Command("miniapp"))
async def on_miniapp(message: types.Message) -> None:
  keyboard = types.InlineKeyboardMarkup(
      inline_keyboard=[[types.InlineKeyboardButton(
          text=_t("bot.open_web_app"),
          web_app=WebAppInfo(url=env.WEBAPP_URL)
      )]]
  )
  await message.answer(_t("bot.open_web_app"), reply_markup=keyboard)


@router.message(F.web_app_data)
async def on_web_app_data(message: types.Message) -> None:
  data = message.web_app_data.data
  if data == "call":
    await message.answer(_t("bot.call_started"))
    summary = await start_vapi_call(message.from_user)
    await message.answer(_t("bot.call_summary", summary=summary))


@router.message(asst_filter)
async def on_change(message: types.Message) -> None:
  await change_assistant(message)


@router.message(mode_filter)
async def on_change_mode(message: types.Message) -> None:
  await change_mode(message)


@router.message(F.voice)
async def on_voice(message: types.Message) -> None:
  text = await decode_voice(message)
  if text:
    text_message = message.model_copy(update={"text": text})
    await handle_response(text_message)


@router.message()
async def on_message(message: types.Message) -> None:
  try:
    await handle_response(message)
  except TypeError as error:
    logger.error(f"on_message:{error}")
    await message.answer(_t("bot.error_in_the_code"))
