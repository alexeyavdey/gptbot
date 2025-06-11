import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional
from aiogram import types
from .logger import create_logger
from .client import client
from .constants import GPT4_MODEL

logger = create_logger(__name__)

# Файл для хранения данных трекера
TRACKER_STORAGE = Path(__file__).parent / "tracker_data.yaml"

# Состояния приветственного модуля
class WelcomeState:
    STEP_1_GREETING = "greeting"
    STEP_2_ANXIETY_INTRO = "anxiety_intro"
    STEP_2_ANXIETY_SURVEY = "anxiety_survey"
    STEP_3_GOALS = "goals"
    STEP_4_NOTIFICATIONS = "notifications"
    STEP_5_AI_MENTOR = "ai_mentor"
    STEP_6_COMPLETION = "completion"
    COMPLETED = "completed"

# Структура данных пользователя трекера
class TrackerUserData:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.step = WelcomeState.STEP_1_GREETING
        self.completed = False
        self.started_at = int(time.time())
        self.anxiety_level = None
        self.anxiety_answers = []
        self.goals = []
        self.custom_goal = None
        self.notifications = {
            "daily_digest": False,
            "deadline_reminders": False,
            "new_task_notifications": False,
            "enabled": True
        }
        self.met_ai_mentor = False
        self.ai_mentor_history = []  # История разговоров с AI-ментором

def load_tracker_data() -> Dict:
    """Загружает данные трекера из YAML файла"""
    try:
        with open(TRACKER_STORAGE, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}
    except Exception as e:
        logger.error(f"Error loading tracker data: {e}")
        return {}

def save_tracker_data(data: Dict):
    """Сохраняет данные трекера в YAML файл"""
    try:
        with open(TRACKER_STORAGE, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        logger.error(f"Error saving tracker data: {e}")

def get_user_data(user_id: int) -> TrackerUserData:
    """Получает данные пользователя трекера"""
    all_data = load_tracker_data()
    user_data_dict = all_data.get(str(user_id), {})
    
    # Создаем объект TrackerUserData
    user_data = TrackerUserData(user_id)
    if user_data_dict:
        user_data.step = user_data_dict.get('step', WelcomeState.STEP_1_GREETING)
        user_data.completed = user_data_dict.get('completed', False)
        user_data.started_at = user_data_dict.get('started_at', int(time.time()))
        user_data.anxiety_level = user_data_dict.get('anxiety_level')
        user_data.anxiety_answers = user_data_dict.get('anxiety_answers', [])
        user_data.goals = user_data_dict.get('goals', [])
        user_data.custom_goal = user_data_dict.get('custom_goal')
        user_data.notifications = user_data_dict.get('notifications', user_data.notifications)
        user_data.met_ai_mentor = user_data_dict.get('met_ai_mentor', False)
        user_data.ai_mentor_history = user_data_dict.get('ai_mentor_history', [])
    
    return user_data

def save_user_data(user_data: TrackerUserData):
    """Сохраняет данные пользователя"""
    all_data = load_tracker_data()
    all_data[str(user_data.user_id)] = {
        'step': user_data.step,
        'completed': user_data.completed,
        'started_at': user_data.started_at,
        'anxiety_level': user_data.anxiety_level,
        'anxiety_answers': user_data.anxiety_answers,
        'goals': user_data.goals,
        'custom_goal': user_data.custom_goal,
        'notifications': user_data.notifications,
        'met_ai_mentor': user_data.met_ai_mentor,
        'ai_mentor_history': user_data.ai_mentor_history
    }
    save_tracker_data(all_data)

def create_progress_bar(current_step: int, total_steps: int = 6) -> str:
    """Создает визуальный прогресс-бар"""
    filled = "●" * current_step
    empty = "○" * (total_steps - current_step)
    return f"{filled}{empty} {current_step}/{total_steps}"

def get_step_number(step: str) -> int:
    """Возвращает номер шага для прогресс-бара"""
    step_mapping = {
        WelcomeState.STEP_1_GREETING: 1,
        WelcomeState.STEP_2_ANXIETY_INTRO: 2,
        WelcomeState.STEP_2_ANXIETY_SURVEY: 2,
        WelcomeState.STEP_3_GOALS: 3,
        WelcomeState.STEP_4_NOTIFICATIONS: 4,
        WelcomeState.STEP_5_AI_MENTOR: 5,
        WelcomeState.STEP_6_COMPLETION: 6,
        WelcomeState.COMPLETED: 6
    }
    return step_mapping.get(step, 1)

# Тексты для опросника тревожности
ANXIETY_QUESTIONS = [
    "Я часто испытываю беспокойство о работе",
    "Мне сложно концентрироваться на задачах", 
    "Я чувствую себя перегруженным обязанностями",
    "Я часто откладываю дела на потом",
    "Меня легко вывести из равновесия стрессовыми ситуациями"
]

# Доступные цели для выбора
AVAILABLE_GOALS = [
    "task_management", "stress_reduction", "productivity", "time_organization"
]

GOAL_DESCRIPTIONS = {
    "task_management": "Управление задачами и расстановка приоритетов",
    "stress_reduction": "Снижение уровня стресса и тревоги", 
    "productivity": "Повышение продуктивности",
    "time_organization": "Организация рабочего времени"
}

# Типы уведомлений
NOTIFICATION_TYPES = {
    "daily_digest": "Ежедневный дайджест задач на день",
    "deadline_reminders": "Напоминание о приближающихся сроках",
    "new_task_notifications": "Уведомления о новых задачах"
}

# Системный промпт для AI-ментора
AI_MENTOR_SYSTEM_PROMPT = """Ты - AI-ментор по управлению стрессом и продуктивностью. Твоя роль - помогать пользователям справляться с рабочей тревожностью и эффективно управлять задачами.

КЛЮЧЕВЫЕ ПРИНЦИПЫ:
• Эмпатия и понимание - всегда проявляй сочувствие к стрессу пользователя
• Практичность - давай конкретные, применимые советы
• Позитивность - поддерживай и мотивируй, избегай критики
• Краткость - отвечай лаконично, но содержательно (до 2-3 предложений)
• Персонализация - учитывай индивидуальные цели и уровень тревожности

СТИЛЬ ОБЩЕНИЯ:
• Дружелюбный, но профессиональный тон
• Используй "я" вместо "мы" для личного подхода
• Задавай уточняющие вопросы для лучшего понимания
• Предлагай конкретные техники и упражнения

ОБЛАСТИ ЭКСПЕРТИЗЫ:
• Техники управления стрессом (дыхательные практики, mindfulness)
• Методы планирования и приоритизации (GTD, Pomodoro, матрица Эйзенхауэра)
• Преодоление прокрастинации
• Баланс работы и отдыха
• Эмоциональная регуляция на рабочем месте

ОГРАНИЧЕНИЯ:
• Не даю медицинские советы или диагнозы
• Не заменяю профессиональную психологическую помощь
• При серьезных проблемах рекомендую обратиться к специалисту

При первом знакомстве представься кратко и узнай, с чем именно пользователь хотел бы получить помощь сегодня."""

def create_ai_mentor_context(user_data: TrackerUserData) -> str:
    """Создает контекст о пользователе для AI-ментора"""
    context_parts = []
    
    # Базовая информация
    context_parts.append(f"Пользователь проходит настройку трекера задач.")
    
    # Уровень тревожности
    if user_data.anxiety_level:
        if user_data.anxiety_level <= 2.0:
            anxiety_desc = "низкий уровень тревожности"
        elif user_data.anxiety_level <= 3.5:
            anxiety_desc = "умеренный уровень тревожности"
        else:
            anxiety_desc = "повышенный уровень тревожности"
        context_parts.append(f"Уровень тревожности: {anxiety_desc} ({user_data.anxiety_level}/5.0).")
    
    # Цели пользователя
    if user_data.goals:
        goal_descriptions = [GOAL_DESCRIPTIONS[goal] for goal in user_data.goals if goal in GOAL_DESCRIPTIONS]
        if goal_descriptions:
            context_parts.append(f"Основные цели: {', '.join(goal_descriptions).lower()}.")
    
    return " ".join(context_parts)

async def chat_with_ai_mentor(user_data: TrackerUserData, user_message: str) -> str:
    """Отправляет сообщение AI-ментору и получает ответ"""
    try:
        # Подготавливаем сообщения для API
        messages = [{"role": "system", "content": AI_MENTOR_SYSTEM_PROMPT}]
        
        # Добавляем контекст о пользователе только при первом общении
        if not user_data.ai_mentor_history:
            context = create_ai_mentor_context(user_data)
            if context:
                messages.append({"role": "system", "content": f"Контекст о пользователе: {context}"})
        
        # Добавляем историю разговоров
        messages.extend(user_data.ai_mentor_history)
        
        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": user_message})
        
        # Отправляем запрос к OpenAI
        response = await client.chat.completions.create(
            model=GPT4_MODEL,
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Сохраняем в историю (только последние 10 сообщений для экономии токенов)
        user_data.ai_mentor_history.append({"role": "user", "content": user_message})
        user_data.ai_mentor_history.append({"role": "assistant", "content": ai_response})
        
        # Ограничиваем историю 20 сообщениями (10 пар вопрос-ответ)
        if len(user_data.ai_mentor_history) > 20:
            user_data.ai_mentor_history = user_data.ai_mentor_history[-20:]
        
        user_data.met_ai_mentor = True
        save_user_data(user_data)
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error in AI mentor chat: {e}")
        return "Извините, сейчас у меня проблемы с соединением. Попробуйте чуть позже."

async def process_tracker_message(message: types.Message):
    """Основная функция обработки сообщений в режиме трекера"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    logger.info(f"Processing tracker message for user {user_id}, step: {user_data.step}")
    
    # Если пользователь уже завершил приветственный модуль
    if user_data.completed:
        await handle_main_tracker_functionality(message, user_data)
        return
    
    # Обработка приветственного модуля
    await handle_welcome_module(message, user_data)

async def process_tracker_callback(callback_query: types.CallbackQuery):
    """Обработка callback-запросов от inline-кнопок трекера"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    user_data = get_user_data(user_id)
    
    logger.info(f"Processing tracker callback for user {user_id}, data: {data}")
    
    await callback_query.answer()  # Убираем "loading" состояние кнопки
    
    # Обработка различных callback-запросов
    if data == "tracker_step_1_next":
        user_data.step = WelcomeState.STEP_2_ANXIETY_INTRO
        save_user_data(user_data)
        await show_step_2_anxiety_intro(callback_query.message, user_data)
    
    elif data == "tracker_anxiety_start":
        user_data.step = WelcomeState.STEP_2_ANXIETY_SURVEY
        user_data.anxiety_answers = []  # Сбрасываем предыдущие ответы
        save_user_data(user_data)
        await handle_anxiety_survey(callback_query.message, user_data)
    
    elif data == "tracker_anxiety_skip":
        user_data.step = WelcomeState.STEP_3_GOALS
        save_user_data(user_data)
        await show_step_3_goals(callback_query.message, user_data)
    
    elif data.startswith("tracker_anxiety_answer_"):
        # Парсим данные: tracker_anxiety_answer_{question_num}_{score}
        parts = data.split("_")
        question_num = int(parts[3])
        score = int(parts[4])
        
        # Расширяем массив ответов при необходимости
        while len(user_data.anxiety_answers) <= question_num:
            user_data.anxiety_answers.append(0)
        
        user_data.anxiety_answers[question_num] = score
        save_user_data(user_data)
        
        # Показываем следующий вопрос
        await show_anxiety_question(callback_query.message, user_data, question_num + 1)
    
    elif data.startswith("tracker_anxiety_back_"):
        # Возврат к предыдущему вопросу
        parts = data.split("_")
        question_num = int(parts[3])
        
        if question_num > 0:
            await show_anxiety_question(callback_query.message, user_data, question_num - 1)
        else:
            # Возврат к введению опросника
            await show_step_2_anxiety_intro(callback_query.message, user_data)
    
    elif data == "tracker_step_3_goals":
        user_data.step = WelcomeState.STEP_3_GOALS
        save_user_data(user_data)
        await show_step_3_goals(callback_query.message, user_data)
    
    elif data.startswith("tracker_goal_toggle_"):
        # Переключение выбора цели
        goal_id = data.replace("tracker_goal_toggle_", "")
        if goal_id in user_data.goals:
            user_data.goals.remove(goal_id)
        else:
            user_data.goals.append(goal_id)
        save_user_data(user_data)
        await show_step_3_goals(callback_query.message, user_data)
    
    elif data == "tracker_step_2_back":
        # Возврат к шагу 2 (опросник тревожности)
        user_data.step = WelcomeState.STEP_2_ANXIETY_INTRO
        save_user_data(user_data)
        await show_step_2_anxiety_intro(callback_query.message, user_data)
    
    elif data == "tracker_step_4_notifications":
        user_data.step = WelcomeState.STEP_4_NOTIFICATIONS
        save_user_data(user_data)
        await show_step_4_notifications(callback_query.message, user_data)
    
    elif data.startswith("tracker_notif_toggle_"):
        # Переключение настройки уведомлений
        notif_id = data.replace("tracker_notif_toggle_", "")
        current_value = user_data.notifications.get(notif_id, False)
        user_data.notifications[notif_id] = not current_value
        save_user_data(user_data)
        await show_step_4_notifications(callback_query.message, user_data)
    
    elif data == "tracker_step_3_back":
        # Возврат к шагу 3 (выбор целей)
        user_data.step = WelcomeState.STEP_3_GOALS
        save_user_data(user_data)
        await show_step_3_goals(callback_query.message, user_data)
    
    elif data == "tracker_step_4_back":
        # Возврат к шагу 4 (уведомления)
        user_data.step = WelcomeState.STEP_4_NOTIFICATIONS
        save_user_data(user_data)
        await show_step_4_notifications(callback_query.message, user_data)
    
    elif data == "tracker_step_5_ai_mentor":
        user_data.step = WelcomeState.STEP_5_AI_MENTOR
        save_user_data(user_data)
        await show_step_5_ai_mentor(callback_query.message, user_data)
    
    elif data == "tracker_meet_ai_mentor":
        await initiate_ai_mentor_chat(callback_query.message, user_data)
    
    elif data == "tracker_ai_mentor_continue":
        # Переключаемся в режим общения с AI-ментором
        text = (
            f"💬 **Общение с AI-ментором**\n\n"
            f"Теперь вы можете задать любой вопрос AI-ментору. "
            f"Он сохранит контекст разговора и будет помнить вашу ситуацию.\n\n"
            f"Просто напишите сообщение, и он ответит!"
        )
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="▶️ Завершить настройку", callback_data="tracker_step_6_completion")]
        ])
        
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    elif data == "tracker_step_6_completion":
        user_data.step = WelcomeState.STEP_6_COMPLETION
        save_user_data(user_data)
        await show_step_6_completion(callback_query.message, user_data)
    
    elif data == "tracker_start_main":
        # Переходим к основному функционалу трекера
        await callback_query.message.edit_text(
            "🎯 **Трекер задач готов к работе!**\n\n"
            "Теперь вы можете использовать основной функционал трекера. "
            "Просто пишите мне, и я помогу вам с организацией задач и управлением стрессом!",
            parse_mode="Markdown"
        )

async def handle_welcome_module(message: types.Message, user_data: TrackerUserData):
    """Обработка приветственного модуля"""
    if user_data.step == WelcomeState.STEP_1_GREETING:
        await show_step_1_greeting(message, user_data)
    elif user_data.step == WelcomeState.STEP_2_ANXIETY_INTRO:
        await show_step_2_anxiety_intro(message, user_data)
    elif user_data.step == WelcomeState.STEP_2_ANXIETY_SURVEY:
        await handle_anxiety_survey(message, user_data)
    elif user_data.step == WelcomeState.STEP_3_GOALS:
        await handle_goals_selection(message, user_data)
    elif user_data.step == WelcomeState.STEP_4_NOTIFICATIONS:
        await handle_notifications_setup(message, user_data)
    elif user_data.step == WelcomeState.STEP_5_AI_MENTOR:
        await handle_ai_mentor_intro(message, user_data)
    elif user_data.step == WelcomeState.STEP_6_COMPLETION:
        await handle_completion(message, user_data)

async def handle_main_tracker_functionality(message: types.Message, user_data: TrackerUserData):
    """Обработка основного функционала трекера (после завершения приветственного модуля)"""
    user_message = message.text.strip()
    
    # Если пользователь общался с AI-ментором, продолжаем общение
    if user_data.met_ai_mentor and user_message:
        ai_response = await chat_with_ai_mentor(user_data, user_message)
        await message.answer(f"🤖 **AI-ментор:**\n\n{ai_response}", parse_mode="Markdown")
        return
    
    # Основной функционал трекера (пока базовый)
    await message.answer(
        "🎯 **Трекер задач активен!**\n\n"
        "Вы можете:\n"
        "• Общаться с AI-ментором (просто пишите вопросы)\n"
        "• Получать советы по управлению стрессом\n"
        "• Планировать задачи и расставлять приоритеты\n\n"
        f"📊 **Ваш профиль:**\n"
        f"• Уровень тревожности: {user_data.anxiety_level or 'не указан'}\n"
        f"• Выбранные цели: {len(user_data.goals)} из {len(GOAL_DESCRIPTIONS)}\n"
        f"• Уведомления: {'включены' if user_data.notifications.get('enabled', True) else 'отключены'}\n\n"
        f"💡 Просто напишите мне, чем могу помочь!",
        parse_mode="Markdown"
    )

# Заглушки для функций шагов - будут реализованы далее
async def show_step_1_greeting(message: types.Message, user_data: TrackerUserData):
    """Шаг 1: Приветствие и объяснение цели"""
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"🎯 **Добро пожаловать в Трекер задач!**\n\n"
        f"Привет! Я ваш личный помощник, разработанный специально для тех, "
        f"кто испытывает тревогу на работе. Я помогу вам организовать задачи, "
        f"расставить приоритеты и научиться справляться со стрессом.\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"🔒 **Важно**: Все ваши данные останутся конфиденциальными и будут "
        f"использоваться только для персонализации вашего опыта."
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="▶️ Начать", callback_data="tracker_step_1_next")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")
    
    logger.info(f"Shown step 1 greeting to user {user_data.user_id}")

async def show_step_2_anxiety_intro(message: types.Message, user_data: TrackerUserData):
    """Шаг 2: Введение в опросник тревожности"""
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"📋 **Шаг 2: Понимание вашего состояния**\n\n"
        f"Чтобы я мог лучше вас понять и адаптировать поддержку, предлагаю "
        f"ответить на несколько вопросов. Это займет всего пару минут.\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"💡 **Как это работает**: Для каждого утверждения выберите, "
        f"насколько оно соответствует вашему опыту:\n"
        f"• 1 - Совсем не согласен\n"
        f"• 2 - Скорее не согласен\n"
        f"• 3 - Затрудняюсь ответить\n"
        f"• 4 - Скорее согласен\n"
        f"• 5 - Полностью согласен"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 Начать опросник", callback_data="tracker_anxiety_start")],
        [types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="tracker_anxiety_skip")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    logger.info(f"Shown step 2 anxiety intro to user {user_data.user_id}")

async def show_anxiety_question(message: types.Message, user_data: TrackerUserData, question_num: int):
    """Показывает вопрос опросника тревожности"""
    if question_num >= len(ANXIETY_QUESTIONS):
        # Все вопросы закончились, переходим к следующему шагу
        await finish_anxiety_survey(message, user_data)
        return
    
    progress = create_progress_bar(get_step_number(user_data.step))
    current_question = ANXIETY_QUESTIONS[question_num]
    
    text = (
        f"📋 **Опросник тревожности**\n\n"
        f"Вопрос {question_num + 1} из {len(ANXIETY_QUESTIONS)}:\n\n"
        f"*{current_question}*\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"Насколько вы согласны с этим утверждением?"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="1", callback_data=f"tracker_anxiety_answer_{question_num}_1"),
            types.InlineKeyboardButton(text="2", callback_data=f"tracker_anxiety_answer_{question_num}_2"),
            types.InlineKeyboardButton(text="3", callback_data=f"tracker_anxiety_answer_{question_num}_3"),
            types.InlineKeyboardButton(text="4", callback_data=f"tracker_anxiety_answer_{question_num}_4"),
            types.InlineKeyboardButton(text="5", callback_data=f"tracker_anxiety_answer_{question_num}_5")
        ],
        [types.InlineKeyboardButton(text="⏮️ Назад", callback_data=f"tracker_anxiety_back_{question_num}")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def finish_anxiety_survey(message: types.Message, user_data: TrackerUserData):
    """Завершает опросник и показывает результаты"""
    if user_data.anxiety_answers:
        avg_score = sum(user_data.anxiety_answers) / len(user_data.anxiety_answers)
        user_data.anxiety_level = round(avg_score, 1)
        
        # Интерпретация результатов
        if avg_score <= 2.0:
            level_text = "Низкий уровень тревожности 😌"
            advice = "У вас хорошие навыки управления стрессом!"
        elif avg_score <= 3.5:
            level_text = "Умеренный уровень тревожности 😐"
            advice = "Иногда стресс может влиять на вашу работу."
        else:
            level_text = "Повышенный уровень тревожности 😰"
            advice = "Трекер поможет вам лучше управлять стрессом."
    else:
        level_text = "Не указан"
        advice = "Вы можете пройти опросник позже в настройках."
    
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"📊 **Результаты опросника**\n\n"
        f"Ваш уровень: {level_text}\n"
        f"{advice}\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"Готовы перейти к выбору ваших целей?"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="▶️ Продолжить", callback_data="tracker_step_3_goals")]
    ])
    
    user_data.step = WelcomeState.STEP_3_GOALS
    save_user_data(user_data)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_anxiety_survey(message: types.Message, user_data: TrackerUserData):
    """Обработка опросника тревожности"""
    # Показываем первый вопрос
    await show_anxiety_question(message, user_data, 0)

async def show_step_3_goals(message: types.Message, user_data: TrackerUserData):
    """Показывает Шаг 3: Выбор целей использования"""
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"🎯 **Шаг 3: Ваши цели**\n\n"
        f"Что вы хотите получить от работы со мной? "
        f"Пожалуйста, выберите наиболее важные для вас пункты:\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"Вы можете выбрать несколько вариантов:"
    )
    
    # Создаем кнопки для каждой цели
    keyboard_rows = []
    for goal_id, goal_desc in GOAL_DESCRIPTIONS.items():
        emoji = "✅" if goal_id in user_data.goals else "☐"
        button_text = f"{emoji} {goal_desc}"
        keyboard_rows.append([types.InlineKeyboardButton(
            text=button_text, 
            callback_data=f"tracker_goal_toggle_{goal_id}"
        )])
    
    # Добавляем кнопки навигации
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⏮️ Назад", callback_data="tracker_step_2_back"),
        types.InlineKeyboardButton(text="▶️ Продолжить", callback_data="tracker_step_4_notifications")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_goals_selection(message: types.Message, user_data: TrackerUserData):
    """Шаг 3: Выбор целей использования"""
    await show_step_3_goals(message, user_data)

async def show_step_4_notifications(message: types.Message, user_data: TrackerUserData):
    """Показывает Шаг 4: Настройка уведомлений"""
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"🔔 **Шаг 4: Уведомления**\n\n"
        f"Чтобы я мог вам помогать вовремя, выберите удобные "
        f"варианты получения уведомлений:\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"Вы можете изменить эти настройки в любое время:"
    )
    
    # Создаем кнопки для каждого типа уведомлений
    keyboard_rows = []
    for notif_id, notif_desc in NOTIFICATION_TYPES.items():
        emoji = "✅" if user_data.notifications.get(notif_id, False) else "☐"
        button_text = f"{emoji} {notif_desc}"
        keyboard_rows.append([types.InlineKeyboardButton(
            text=button_text, 
            callback_data=f"tracker_notif_toggle_{notif_id}"
        )])
    
    # Кнопка для полного отключения уведомлений
    enabled_emoji = "✅" if user_data.notifications.get("enabled", True) else "☐"
    keyboard_rows.append([types.InlineKeyboardButton(
        text=f"{enabled_emoji} Включить уведомления", 
        callback_data="tracker_notif_toggle_enabled"
    )])
    
    # Добавляем кнопки навигации
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⏮️ Назад", callback_data="tracker_step_3_back"),
        types.InlineKeyboardButton(text="▶️ Продолжить", callback_data="tracker_step_5_ai_mentor")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_notifications_setup(message: types.Message, user_data: TrackerUserData):
    """Шаг 4: Настройка уведомлений"""
    await show_step_4_notifications(message, user_data)

async def show_step_5_ai_mentor(message: types.Message, user_data: TrackerUserData):
    """Показывает Шаг 5: Знакомство с AI-ментором"""
    progress = create_progress_bar(get_step_number(user_data.step))
    
    text = (
        f"🤖 **Шаг 5: Знакомство с AI-ментором**\n\n"
        f"Я также могу предложить вам поддержку от моего AI-ментора. "
        f"Он поможет с управлением временем, приоритизацией задач "
        f"и даст советы по работе со стрессом.\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"💡 **AI-ментор умеет:**\n"
        f"• Давать персональные советы по управлению стрессом\n"
        f"• Помогать с планированием и приоритизацией\n"
        f"• Предлагать техники борьбы с прокрастинацией\n"
        f"• Поддерживать в сложных ситуациях\n\n"
        f"Хотите познакомиться с ним?"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👋 Познакомиться", callback_data="tracker_meet_ai_mentor")],
        [
            types.InlineKeyboardButton(text="⏮️ Назад", callback_data="tracker_step_4_back"),
            types.InlineKeyboardButton(text="⏭️ Пропустить", callback_data="tracker_step_6_completion")
        ]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def initiate_ai_mentor_chat(message: types.Message, user_data: TrackerUserData):
    """Инициирует первое общение с AI-ментором"""
    # Отправляем приветственное сообщение ментору
    welcome_message = "Привет! Это наша первая встреча в рамках настройки трекера задач."
    
    await message.edit_text("🤖 Соединяюсь с AI-ментором...", parse_mode="Markdown")
    
    ai_response = await chat_with_ai_mentor(user_data, welcome_message)
    
    text = (
        f"🤖 **AI-ментор подключился!**\n\n"
        f"{ai_response}\n\n"
        f"💬 Вы можете задать ему любой вопрос или продолжить настройку трекера."
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Продолжить общение", callback_data="tracker_ai_mentor_continue")],
        [types.InlineKeyboardButton(text="▶️ Завершить настройку", callback_data="tracker_step_6_completion")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_ai_mentor_intro(message: types.Message, user_data: TrackerUserData):
    """Шаг 5: Знакомство с AI-ментором"""
    await show_step_5_ai_mentor(message, user_data)

async def show_step_6_completion(message: types.Message, user_data: TrackerUserData):
    """Показывает Шаг 6: Завершение приветственного модуля"""
    progress = create_progress_bar(6)  # Финальный шаг
    
    # Подготавливаем сводку настроек
    anxiety_text = "не указан"
    if user_data.anxiety_level:
        if user_data.anxiety_level <= 2.0:
            anxiety_text = "низкий 😌"
        elif user_data.anxiety_level <= 3.5:
            anxiety_text = "умеренный 😐"
        else:
            anxiety_text = "повышенный 😰"
    
    goals_text = "не выбраны"
    if user_data.goals:
        goal_names = [GOAL_DESCRIPTIONS[goal] for goal in user_data.goals if goal in GOAL_DESCRIPTIONS]
        goals_text = ", ".join(goal_names).lower()
    
    notifications_text = "включены" if user_data.notifications.get("enabled", True) else "отключены"
    ai_mentor_text = "да" if user_data.met_ai_mentor else "нет"
    
    text = (
        f"🎉 **Поздравляем! Настройка завершена**\n\n"
        f"Спасибо, что прошли приветственный модуль! "
        f"Я готов помочь вам в управлении задачами и снижении стресса.\n\n"
        f"📊 Прогресс: {progress}\n\n"
        f"📋 **Ваши настройки:**\n"
        f"• Уровень тревожности: {anxiety_text}\n"
        f"• Цели: {goals_text}\n"
        f"• Уведомления: {notifications_text}\n"
        f"• Знакомство с AI-ментором: {ai_mentor_text}\n\n"
        f"🚀 Теперь вы можете начать использовать трекер задач! "
        f"Все настройки можно изменить в любое время."
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎯 Начать работу с трекером", callback_data="tracker_start_main")]
    ])
    
    # Помечаем приветственный модуль как завершенный
    user_data.completed = True
    user_data.step = WelcomeState.COMPLETED
    save_user_data(user_data)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_completion(message: types.Message, user_data: TrackerUserData):
    """Шаг 6: Завершение приветственного модуля"""
    await show_step_6_completion(message, user_data)