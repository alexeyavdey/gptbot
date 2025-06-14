import time
import asyncio
from typing import List
from openai.types import beta
from aiogram import types

from .client import client, get_thread, get_assistant
from .logger import create_logger
from .translate import _t
from . import config
from .helpers import ChatActions, is_valid_markdown, escape_markdown
from .users import is_group_bot
from .message_queues import QueueController, thread_lock
from .modes import get_mode
from .file_search import search_context
from .constants import GPT4_MODEL, O3_MODEL
from .tracker import process_tracker_message
from .enhanced_ai_agents import initialize_enhanced_agents
from . import env
import os


logger = create_logger(__name__)

model_history = {}
api_key=os.environ['OPENAI_API_KEY']

# Инициализация AI-агентов
orchestrator_agent = None

def get_orchestrator():
    global orchestrator_agent
    if orchestrator_agent is None:
        try:
            logger.info(f"api: {api_key}")
            orchestrator_agent = initialize_enhanced_agents(api_key, GPT4_MODEL)
            logger.info("Enhanced AI agents initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced AI agents: {e}")
    return orchestrator_agent

def reset_orchestrator():
    """Принудительно пересоздать оркестратор (для применения обновлений кода)"""
    global orchestrator_agent
    orchestrator_agent = None
    logger.info("Orchestrator reset - will be recreated on next use")


async def change_assistant(message: types.Message):
  tutor = message.text
  user_id = message.from_user.id
  await message.answer(_t("bot.your_tutor", tutor=tutor), reply_markup=types.ReplyKeyboardRemove())
  assistant = await get_assistant(user_id, tutor)
  logger.info(f"new_assistant:{user_id}:{tutor}:{assistant.id}")


async def change_mode(message: types.Message):
  mode = message.text
  user_id = message.from_user.id
  await get_mode(user_id, mode)
  await message.answer(_t("bot.your_mode", mode=mode), reply_markup=types.ReplyKeyboardRemove())
  logger.info(f"new_mode:{user_id}:{mode}")


def clear_history(user_id):
  model_history.pop(user_id, None)


async def handle_response(message: types.Message):
  user_id = message.from_user.id
  username = message.from_user.username

  logger.info(f"user:{username}:{user_id}\n\t{message.md_text}")

  mode = await get_mode(user_id)
  if mode == "tracker":
    await process_tracker_message_with_agents(message)
    return
  elif mode != "assistant":
    await process_model_message(user_id, message)
    return

  thread = await get_thread(user_id)
  logger.debug(f"handle_response:{thread}")

  if not QueueController.start_queue(thread, message):
    return

  assistant = await get_assistant(user_id)
  logger.debug(f"handle_response:{assistant}")

  delay = config.GROUP_BOT_RESPONSE_DELAY if is_group_bot() else config.BOT_RESPONSE_DELAY
  if delay > 0:
    await QueueController.wait_next(delay, thread, user_id)

  async with thread_lock(thread.id, user_id) as messages:
    await add_messages_to_thread(thread, messages)
    await process_message(thread, assistant, message)


async def process_message(thread: beta.Thread, assistant: beta.Assistant, message: types.Message):
  logger.debug(f"process_message:{thread.id}:{message.message_id}")

  run = await client.beta.threads.runs.create(
      thread.id,
      assistant_id=assistant.id,
      instructions=_t("gpt.instructions",
                      name=message.from_user.first_name,
                      id=message.from_user.id,
                      full_name=message.from_user.full_name,
                      instructions=assistant.instructions)
  )

  start_time = time.time()
  while True:
    logger.info(f"process_message:status:{run.status}")

    if run.status == "completed":
      await retrieve_messages(thread.id, run.id, message)
      logger.info("process_message:done")
      break
    elif run.status in ["failed", "cancelled", "expired"]:
      logger.info("process_message:failed")
      break
    else:
      await ChatActions.send_typing(message)
      await asyncio.sleep(config.RUN_STATUS_POLL_INTERVAL)

    run = await client.beta.threads.runs.retrieve(
        run.id,
        thread_id=thread.id
    )
  end_time = time.time()
  logger.debug(f"process_message:reponse time: {end_time - start_time:.2f}s")


async def retrieve_messages(thread_id, run_id, message: types.Message):
  run_steps = await client.beta.threads.runs.steps.list(
      thread_id=thread_id,
      run_id=run_id
  )

  for step in run_steps.data:
    if step.type == "message_creation":
      message_id = step.step_details.message_creation.message_id

      msg = await client.beta.threads.messages.retrieve(
          message_id=message_id,
          thread_id=thread_id
      )

      content = msg.content[0].text.value
      if content:
        escaped = not is_valid_markdown(content)
        if escaped:
          content = escape_markdown(content)
        logger.info(f"retrieve_messages:{msg.role}:{step.assistant_id}:escaped={escaped}:\n\t{content}")
        await message.answer(content)


async def add_messages_to_thread(thread: beta.Thread, messages: List[types.Message]):
  user_request = await client.beta.threads.messages.create(
      thread.id,
      role="user",
      content="\n".join(message.md_text for message in messages)
  )
  logger.debug(f"add_message_to_thread:{user_request.id}")


async def process_model_message(user_id: int, message: types.Message):
  # Получаем тред пользователя для синхронизации с Assistant API
  thread = await get_thread(user_id)
  
  # Добавляем контекст из RAG в начале если нужен
  context = await search_context(user_id, message.text)
  history = []
  if context:
    logger.info(f"process_model_message:use_vector_store:{user_id}")
    history.append({"role": "system", "content": f"Context:\n{context}"})
  
  # Загружаем историю из треда OpenAI
  thread_messages = await client.beta.threads.messages.list(thread_id=thread.id, limit=50)
  
  # Конвертируем сообщения из треда в формат chat completions
  for msg in reversed(thread_messages.data):
    if msg.role == "user":
      history.append({"role": "user", "content": msg.content[0].text.value})
    elif msg.role == "assistant":
      history.append({"role": "assistant", "content": msg.content[0].text.value})
  
  # Добавляем текущее сообщение пользователя
  history.append({"role": "user", "content": message.text})

  mode = await get_mode(user_id)
  model = GPT4_MODEL if mode == "gpt-4.1" else O3_MODEL

  response = await client.chat.completions.create(
      model=model,
      messages=history,
  )
  reply = response.choices[0].message.content
  
  # Сохраняем сообщения в тред OpenAI для синхронизации
  await client.beta.threads.messages.create(
      thread.id,
      role="user", 
      content=message.text
  )
  await client.beta.threads.messages.create(
      thread.id,
      role="assistant",
      content=reply
  )
  
  await message.answer(reply)


async def process_tracker_message_with_agents(message: types.Message):
    """Обработка сообщений трекера через AI-агентов"""
    user_id = message.from_user.id
    orchestrator = get_orchestrator()
    
    if not orchestrator:
        logger.error("Orchestrator agent not available, falling back to original tracker")
        await process_tracker_message(message)
        return
    
    try:
        # Отправляем запрос оркестратору
        result = await orchestrator.route_request(user_id, message.text)
        
        if result["agent"] == "error":
            logger.error(f"Error from orchestrator: {result['response']}")
            await message.answer("Произошла ошибка при обработке запроса.")
        else:
            # Проверяем длину ответа и разбиваем если необходимо
            response = result["response"]
            if len(response) > 4096:
                # Разбиваем длинное сообщение на части
                chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
                for chunk in chunks:
                    await message.answer(chunk)
            else:
                await message.answer(response)
                
        logger.info(f"Tracker message processed by agent: {result['agent']}")
        
    except Exception as e:
        logger.error(f"Error processing tracker message with agents: {e}")
        # Fallback к оригинальной функции
        await process_tracker_message(message)


async def process_tracker_callback_with_agents(callback_query: types.CallbackQuery):
    """Обработка callback запросов трекера через AI-агентов"""
    # Пока что оставляем callback обработку как есть,
    # так как она в основном связана с UI навигацией
    from .tracker import process_tracker_callback
    await process_tracker_callback(callback_query)
