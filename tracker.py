import yaml
import time
from pathlib import Path
from typing import Dict, List, Optional
from aiogram import types
from .logger import create_logger
from .client import client
from .constants import GPT4_MODEL
import uuid
from datetime import datetime, timedelta
import pytz

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

# Статусы задач
class TaskStatus:
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

# Приоритеты задач
class TaskPriority:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

# Структура задачи
class TrackerTask:
    def __init__(self, title: str, description: str = "", priority: str = TaskPriority.MEDIUM):
        self.id = str(uuid.uuid4())
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = int(time.time())
        self.updated_at = int(time.time())
        self.due_date = None
        self.completed_at = None
    
    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'priority': self.priority,
            'status': self.status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'due_date': self.due_date,
            'completed_at': self.completed_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TrackerTask':
        task = cls(data['title'], data.get('description', ''), data.get('priority', TaskPriority.MEDIUM))
        task.id = data['id']
        task.status = data.get('status', TaskStatus.PENDING)
        task.created_at = data.get('created_at', int(time.time()))
        task.updated_at = data.get('updated_at', int(time.time()))
        task.due_date = data.get('due_date')
        task.completed_at = data.get('completed_at')
        return task

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
        self.tasks = []  # Массив задач пользователя
        self.current_view = "main"  # Текущий вид интерфейса (main, tasks, add_task, etc.)
        self.timezone = "UTC"  # Часовой пояс пользователя
        self.notification_time = "09:00"  # Время для ежедневных уведомлений

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
        
        # Загружаем задачи
        tasks_data = user_data_dict.get('tasks', [])
        user_data.tasks = [TrackerTask.from_dict(task_dict) for task_dict in tasks_data]
        user_data.current_view = user_data_dict.get('current_view', 'main')
        user_data.timezone = user_data_dict.get('timezone', 'UTC')
        user_data.notification_time = user_data_dict.get('notification_time', '09:00')
    
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
        'ai_mentor_history': user_data.ai_mentor_history,
        'tasks': [task.to_dict() for task in user_data.tasks],
        'current_view': user_data.current_view,
        'timezone': user_data.timezone,
        'notification_time': user_data.notification_time
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

# Описания приоритетов задач
PRIORITY_DESCRIPTIONS = {
    TaskPriority.LOW: "🟢 Низкий",
    TaskPriority.MEDIUM: "🟡 Средний", 
    TaskPriority.HIGH: "🟠 Высокий",
    TaskPriority.URGENT: "🔴 Срочный"
}

# Описания статусов задач
STATUS_DESCRIPTIONS = {
    TaskStatus.PENDING: "⏳ Ожидает",
    TaskStatus.IN_PROGRESS: "🔄 В работе",
    TaskStatus.COMPLETED: "✅ Выполнена",
    TaskStatus.CANCELLED: "❌ Отменена"
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

# === CRUD операции для задач ===

def create_task(user_data: TrackerUserData, title: str, description: str = "", priority: str = TaskPriority.MEDIUM) -> TrackerTask:
    """Создает новую задачу"""
    task = TrackerTask(title, description, priority)
    user_data.tasks.append(task)
    save_user_data(user_data)
    logger.info(f"Created task '{title}' for user {user_data.user_id}")
    
    # Отправляем уведомление о новой задаче (если включены)
    try:
        from .notifications import get_notification_manager
        notification_manager = get_notification_manager()
        if notification_manager.bot:
            import asyncio
            asyncio.create_task(notification_manager.notify_new_task(user_data.user_id, title))
    except Exception as e:
        logger.error(f"Error sending new task notification: {e}")
    
    return task

def get_task_by_id(user_data: TrackerUserData, task_id: str) -> Optional[TrackerTask]:
    """Получает задачу по ID"""
    for task in user_data.tasks:
        if task.id == task_id:
            return task
    return None

def update_task_status(user_data: TrackerUserData, task_id: str, new_status: str) -> bool:
    """Обновляет статус задачи"""
    task = get_task_by_id(user_data, task_id)
    if task:
        task.status = new_status
        task.updated_at = int(time.time())
        if new_status == TaskStatus.COMPLETED:
            task.completed_at = int(time.time())
        save_user_data(user_data)
        logger.info(f"Updated task {task_id} status to {new_status} for user {user_data.user_id}")
        return True
    return False

def update_task_priority(user_data: TrackerUserData, task_id: str, new_priority: str) -> bool:
    """Обновляет приоритет задачи"""
    task = get_task_by_id(user_data, task_id)
    if task:
        task.priority = new_priority
        task.updated_at = int(time.time())
        save_user_data(user_data)
        logger.info(f"Updated task {task_id} priority to {new_priority} for user {user_data.user_id}")
        return True
    return False

def delete_task(user_data: TrackerUserData, task_id: str) -> bool:
    """Удаляет задачу"""
    for i, task in enumerate(user_data.tasks):
        if task.id == task_id:
            removed_task = user_data.tasks.pop(i)
            save_user_data(user_data)
            logger.info(f"Deleted task '{removed_task.title}' for user {user_data.user_id}")
            return True
    return False

def get_tasks_by_status(user_data: TrackerUserData, status: str) -> List[TrackerTask]:
    """Получает задачи по статусу"""
    return [task for task in user_data.tasks if task.status == status]

def get_tasks_by_priority(user_data: TrackerUserData, priority: str) -> List[TrackerTask]:
    """Получает задачи по приоритету"""
    return [task for task in user_data.tasks if task.priority == priority]

def get_tasks_sorted(user_data: TrackerUserData, sort_by: str = "created_at") -> List[TrackerTask]:
    """Получает отсортированные задачи"""
    if sort_by == "priority":
        priority_order = {TaskPriority.URGENT: 4, TaskPriority.HIGH: 3, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 1}
        return sorted(user_data.tasks, key=lambda t: (priority_order.get(t.priority, 0), -t.created_at), reverse=True)
    elif sort_by == "status":
        status_order = {TaskStatus.IN_PROGRESS: 4, TaskStatus.PENDING: 3, TaskStatus.COMPLETED: 2, TaskStatus.CANCELLED: 1}
        return sorted(user_data.tasks, key=lambda t: (status_order.get(t.status, 0), -t.created_at), reverse=True)
    else:  # created_at
        return sorted(user_data.tasks, key=lambda t: t.created_at, reverse=True)

def format_task_text(task: TrackerTask, show_details: bool = False, user_data: TrackerUserData = None) -> str:
    """Форматирует текст задачи для отображения"""
    status_emoji = STATUS_DESCRIPTIONS.get(task.status, "⚪")
    priority_emoji = PRIORITY_DESCRIPTIONS.get(task.priority, "⚪")
    
    text = f"{status_emoji} **{task.title}**"
    
    if show_details:
        if task.description:
            text += f"\n📝 {task.description}"
        text += f"\n🎯 Приоритет: {priority_emoji}"
        
        # Используем пользовательский часовой пояс если доступен
        if user_data:
            created_time = format_datetime_for_user(task.created_at, user_data)
            text += f"\n📅 Создана: {created_time}"
            if task.status == TaskStatus.COMPLETED and task.completed_at:
                completed_time = format_datetime_for_user(task.completed_at, user_data)
                text += f"\n✅ Завершена: {completed_time}"
            if task.due_date:
                due_time = format_datetime_for_user(task.due_date, user_data)
                text += f"\n⏰ Дедлайн: {due_time}"
        else:
            text += f"\n📅 Создана: {datetime.fromtimestamp(task.created_at).strftime('%d.%m.%Y %H:%M')}"
            if task.status == TaskStatus.COMPLETED and task.completed_at:
                text += f"\n✅ Завершена: {datetime.fromtimestamp(task.completed_at).strftime('%d.%m.%Y %H:%M')}"
            if task.due_date:
                text += f"\n⏰ Дедлайн: {datetime.fromtimestamp(task.due_date).strftime('%d.%m.%Y %H:%M')}"
    
    return text

# === Функции для работы с часовыми поясами ===

def get_user_local_time(user_data: TrackerUserData) -> datetime:
    """Получает текущее время в часовом поясе пользователя"""
    try:
        user_tz = pytz.timezone(user_data.timezone)
        return datetime.now(user_tz)
    except:
        return datetime.now(pytz.UTC)

def format_datetime_for_user(timestamp: int, user_data: TrackerUserData) -> str:
    """Форматирует timestamp в строку с учетом часового пояса пользователя"""
    try:
        user_tz = pytz.timezone(user_data.timezone)
        dt = datetime.fromtimestamp(timestamp, tz=user_tz)
        return dt.strftime('%d.%m.%Y %H:%M')
    except:
        dt = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
        return dt.strftime('%d.%m.%Y %H:%M UTC')

def parse_user_time(time_str: str, user_data: TrackerUserData) -> Optional[int]:
    """Парсит время пользователя в timestamp с учетом часового пояса"""
    try:
        user_tz = pytz.timezone(user_data.timezone)
        
        # Пробуем разные форматы
        formats = ['%H:%M', '%d.%m.%Y %H:%M', '%d.%m %H:%M']
        
        for fmt in formats:
            try:
                if fmt == '%H:%M':
                    # Только время - используем сегодняшнюю дату
                    today = get_user_local_time(user_data).date()
                    parsed_time = datetime.strptime(time_str, fmt).time()
                    dt = user_tz.localize(datetime.combine(today, parsed_time))
                else:
                    # Полная дата и время
                    dt = user_tz.localize(datetime.strptime(time_str, fmt))
                
                return int(dt.timestamp())
            except ValueError:
                continue
        
        return None
    except:
        return None

def get_common_timezones() -> Dict[str, str]:
    """Возвращает список популярных часовых поясов"""
    return {
        "Europe/Moscow": "🇷🇺 Москва (UTC+3)",
        "Europe/Kiev": "🇺🇦 Киев (UTC+2)",
        "Europe/Minsk": "🇧🇾 Минск (UTC+3)",
        "Asia/Almaty": "🇰🇿 Алматы (UTC+6)",
        "Asia/Tashkent": "🇺🇿 Ташкент (UTC+5)",
        "Asia/Yerevan": "🇦🇲 Ереван (UTC+4)",
        "Asia/Baku": "🇦🇿 Баку (UTC+4)",
        "Europe/London": "🇬🇧 Лондон (UTC+0)",
        "Europe/Berlin": "🇩🇪 Берлин (UTC+1)",
        "America/New_York": "🇺🇸 Нью-Йорк (UTC-5)",
        "Asia/Tokyo": "🇯🇵 Токио (UTC+9)",
        "UTC": "🌍 UTC (Всемирное время)"
    }

def detect_timezone_from_locale() -> str:
    """Пытается определить часовой пояс по системной локали"""
    try:
        import locale
        lang = locale.getdefaultlocale()[0]
        
        # Простое определение по языку
        timezone_map = {
            'ru_RU': 'Europe/Moscow',
            'uk_UA': 'Europe/Kiev',
            'be_BY': 'Europe/Minsk',
            'kk_KZ': 'Asia/Almaty',
            'uz_UZ': 'Asia/Tashkent'
        }
        
        return timezone_map.get(lang, 'UTC')
    except:
        return 'UTC'

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
        await show_main_menu(callback_query.message, user_data)
    
    # === Обработка новых callback для управления задачами ===
    
    elif data == "tracker_main_menu":
        await show_main_menu(callback_query.message, user_data)
    
    elif data == "tracker_show_tasks":
        await show_tasks_menu(callback_query.message, user_data)
    
    elif data == "tracker_new_task":
        await start_task_creation(callback_query.message, user_data)
    
    elif data == "tracker_cancel_creation":
        user_data.current_view = "main"
        save_user_data(user_data)
        await show_main_menu(callback_query.message, user_data)
    
    elif data.startswith("tracker_task_detail_"):
        task_id = data.replace("tracker_task_detail_", "")
        await show_task_detail(callback_query.message, user_data, task_id)
    
    elif data.startswith("tracker_start_task_"):
        task_id = data.replace("tracker_start_task_", "")
        if update_task_status(user_data, task_id, TaskStatus.IN_PROGRESS):
            await callback_query.message.edit_text(
                "▶️ **Задача взята в работу!**\n\nУдачи в выполнении! AI-ментор всегда готов помочь советом.",
                parse_mode="Markdown"
            )
            await show_task_detail(callback_query.message, user_data, task_id)
        else:
            await callback_query.message.edit_text("❌ Ошибка при обновлении задачи", parse_mode="Markdown")
    
    elif data.startswith("tracker_complete_task_"):
        task_id = data.replace("tracker_complete_task_", "")
        if update_task_status(user_data, task_id, TaskStatus.COMPLETED):
            task = get_task_by_id(user_data, task_id)
            await callback_query.message.edit_text(
                f"✅ **Поздравляем!**\n\nЗадача '{task.title if task else 'Неизвестная'}' успешно завершена!",
                parse_mode="Markdown"
            )
            await show_tasks_menu(callback_query.message, user_data)
        else:
            await callback_query.message.edit_text("❌ Ошибка при обновлении задачи", parse_mode="Markdown")
    
    elif data.startswith("tracker_pause_task_"):
        task_id = data.replace("tracker_pause_task_", "")
        if update_task_status(user_data, task_id, TaskStatus.PENDING):
            await show_task_detail(callback_query.message, user_data, task_id)
        else:
            await callback_query.message.edit_text("❌ Ошибка при обновлении задачи", parse_mode="Markdown")
    
    elif data.startswith("tracker_reopen_task_"):
        task_id = data.replace("tracker_reopen_task_", "")
        if update_task_status(user_data, task_id, TaskStatus.PENDING):
            await show_task_detail(callback_query.message, user_data, task_id)
        else:
            await callback_query.message.edit_text("❌ Ошибка при обновлении задачи", parse_mode="Markdown")
    
    elif data.startswith("tracker_delete_task_"):
        task_id = data.replace("tracker_delete_task_", "")
        task = get_task_by_id(user_data, task_id)
        if task:
            text = f"🗑️ **Удаление задачи**\n\n{format_task_text(task, show_details=True, user_data=user_data)}\n\nВы уверены, что хотите удалить эту задачу?"
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"tracker_confirm_delete_{task_id}"),
                    types.InlineKeyboardButton(text="❌ Отмена", callback_data=f"tracker_task_detail_{task_id}")
                ]
            ])
            await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    elif data.startswith("tracker_confirm_delete_"):
        task_id = data.replace("tracker_confirm_delete_", "")
        task = get_task_by_id(user_data, task_id)
        task_title = task.title if task else "Неизвестная"
        if delete_task(user_data, task_id):
            await callback_query.message.edit_text(
                f"🗑️ **Задача удалена**\n\nЗадача '{task_title}' была успешно удалена.",
                parse_mode="Markdown"
            )
            await show_tasks_menu(callback_query.message, user_data)
        else:
            await callback_query.message.edit_text("❌ Ошибка при удалении задачи", parse_mode="Markdown")
    
    elif data.startswith("tracker_edit_priority_"):
        task_id = data.replace("tracker_edit_priority_", "")
        await show_priority_selection(callback_query.message, user_data, task_id)
    
    elif data.startswith("tracker_set_priority_"):
        # Формат: tracker_set_priority_{task_id}_{priority}
        parts = data.replace("tracker_set_priority_", "").split("_", 1)
        if len(parts) == 2:
            task_id, priority = parts
            if update_task_priority(user_data, task_id, priority):
                await show_task_detail(callback_query.message, user_data, task_id)
            else:
                await callback_query.message.edit_text("❌ Ошибка при обновлении приоритета", parse_mode="Markdown")
    
    elif data == "tracker_ai_mentor_chat":
        text = (
            f"🤖 **AI-ментор готов помочь!**\n\n"
            f"Просто напишите ваш вопрос, и я передам его AI-ментору. "
            f"Он поможет с планированием, управлением стрессом и повышением продуктивности."
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="tracker_main_menu")]
        ])
        await callback_query.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    
    elif data == "tracker_settings":
        await show_settings_menu(callback_query.message, user_data)
    
    elif data.startswith("tracker_filter_"):
        filter_type = data.replace("tracker_filter_", "")
        await show_filtered_tasks(callback_query.message, user_data, filter_type)
    
    # === Обработка настроек ===
    
    elif data == "tracker_settings_notifications":
        await show_notification_settings(callback_query.message, user_data)
    
    elif data == "tracker_settings_timezone":
        await show_timezone_settings(callback_query.message, user_data)
    
    elif data.startswith("tracker_set_timezone_"):
        timezone = data.replace("tracker_set_timezone_", "")
        user_data.timezone = timezone
        save_user_data(user_data)
        await show_timezone_settings(callback_query.message, user_data)
    
    elif data == "tracker_test_digest":
        # Отправляем тестовый дайджест
        try:
            from .notifications import get_notification_manager
            notification_manager = get_notification_manager()
            await notification_manager.send_manual_digest(user_data.user_id)
            await callback_query.answer("📬 Тестовый дайджест отправлен!")
        except Exception as e:
            logger.error(f"Error sending test digest: {e}")
            await callback_query.answer("❌ Ошибка отправки дайджеста")

async def show_priority_selection(message: types.Message, user_data: TrackerUserData, task_id: str):
    """Показывает меню выбора приоритета"""
    task = get_task_by_id(user_data, task_id)
    if not task:
        await message.edit_text("❌ Задача не найдена", parse_mode="Markdown")
        return
    
    text = (
        f"🎯 **Изменение приоритета**\n\n"
        f"Задача: {task.title}\n"
        f"Текущий приоритет: {PRIORITY_DESCRIPTIONS.get(task.priority, 'Неизвестно')}\n\n"
        f"Выберите новый приоритет:"
    )
    
    keyboard_rows = []
    for priority, description in PRIORITY_DESCRIPTIONS.items():
        keyboard_rows.append([types.InlineKeyboardButton(
            text=description, 
            callback_data=f"tracker_set_priority_{task_id}_{priority}"
        )])
    
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⬅️ Назад", callback_data=f"tracker_task_detail_{task_id}")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def show_filtered_tasks(message: types.Message, user_data: TrackerUserData, filter_type: str):
    """Показывает отфильтрованные задачи"""
    if filter_type == "in_progress":
        filtered_tasks = get_tasks_by_status(user_data, TaskStatus.IN_PROGRESS)
        title = "🔄 Задачи в работе"
    elif filter_type == "completed":
        filtered_tasks = get_tasks_by_status(user_data, TaskStatus.COMPLETED)
        title = "✅ Выполненные задачи"
    else:
        filtered_tasks = user_data.tasks
        title = "📋 Все задачи"
    
    if not filtered_tasks:
        text = f"{title}\n\nЗадач в этой категории пока нет."
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="⬅️ К задачам", callback_data="tracker_show_tasks")]
        ])
    else:
        text = f"{title} ({len(filtered_tasks)})\n\n"
        
        for i, task in enumerate(filtered_tasks[:10]):
            text += f"{i+1}. {format_task_text(task, user_data=user_data)}\n"
        
        if len(filtered_tasks) > 10:
            text += f"\n... и еще {len(filtered_tasks) - 10} задач"
        
        keyboard_rows = []
        for i, task in enumerate(filtered_tasks[:5]):
            button_text = f"{i+1}. {task.title[:20]}{'...' if len(task.title) > 20 else ''}"
            keyboard_rows.append([types.InlineKeyboardButton(
                text=button_text, 
                callback_data=f"tracker_task_detail_{task.id}"
            )])
        
        keyboard_rows.append([
            types.InlineKeyboardButton(text="⬅️ К задачам", callback_data="tracker_show_tasks")
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

# === Функции настроек ===

async def show_settings_menu(message: types.Message, user_data: TrackerUserData):
    """Показывает меню настроек"""
    current_time = get_user_local_time(user_data).strftime('%H:%M')
    timezone_name = get_common_timezones().get(user_data.timezone, f"🌍 {user_data.timezone}")
    
    text = (
        f"⚙️ **Настройки трекера**\n\n"
        f"🕘 **Часовой пояс:** {timezone_name}\n"
        f"⏰ **Текущее время:** {current_time}\n"
        f"📬 **Время уведомлений:** {user_data.notification_time}\n\n"
        f"📊 **Статус уведомлений:**\n"
        f"• Система: {'✅' if user_data.notifications.get('enabled', True) else '❌'} {'Включена' if user_data.notifications.get('enabled', True) else 'Отключена'}\n"
        f"• Дайджест: {'✅' if user_data.notifications.get('daily_digest', False) else '❌'}\n"
        f"• Дедлайны: {'✅' if user_data.notifications.get('deadline_reminders', False) else '❌'}\n"
        f"• Новые задачи: {'✅' if user_data.notifications.get('new_task_notifications', False) else '❌'}"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔔 Уведомления", callback_data="tracker_settings_notifications")],
        [types.InlineKeyboardButton(text="🌍 Часовой пояс", callback_data="tracker_settings_timezone")],
        [types.InlineKeyboardButton(text="📬 Тестовый дайджест", callback_data="tracker_test_digest")],
        [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="tracker_main_menu")]
    ])
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def show_notification_settings(message: types.Message, user_data: TrackerUserData):
    """Показывает настройки уведомлений"""
    text = (
        f"🔔 **Настройки уведомлений**\n\n"
        f"Выберите типы уведомлений, которые хотите получать:"
    )
    
    keyboard_rows = []
    
    # Главный переключатель
    enabled_emoji = "✅" if user_data.notifications.get('enabled', True) else "❌"
    keyboard_rows.append([types.InlineKeyboardButton(
        text=f"{enabled_emoji} Включить уведомления", 
        callback_data="tracker_notif_toggle_enabled"
    )])
    
    # Типы уведомлений
    for notif_id, notif_desc in NOTIFICATION_TYPES.items():
        emoji = "✅" if user_data.notifications.get(notif_id, False) else "☐"
        button_text = f"{emoji} {notif_desc}"
        keyboard_rows.append([types.InlineKeyboardButton(
            text=button_text, 
            callback_data=f"tracker_notif_toggle_{notif_id}"
        )])
    
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⬅️ Настройки", callback_data="tracker_settings")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

async def show_timezone_settings(message: types.Message, user_data: TrackerUserData):
    """Показывает настройки часового пояса"""
    current_tz = user_data.timezone
    current_time = get_user_local_time(user_data).strftime('%H:%M')
    
    text = (
        f"🌍 **Выбор часового пояса**\n\n"
        f"Текущий: {get_common_timezones().get(current_tz, current_tz)}\n"
        f"Время: {current_time}\n\n"
        f"Выберите ваш часовой пояс:"
    )
    
    keyboard_rows = []
    timezones = get_common_timezones()
    
    for tz_id, tz_desc in timezones.items():
        emoji = "✅ " if tz_id == current_tz else ""
        keyboard_rows.append([types.InlineKeyboardButton(
            text=f"{emoji}{tz_desc}", 
            callback_data=f"tracker_set_timezone_{tz_id}"
        )])
    
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⬅️ Настройки", callback_data="tracker_settings")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

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
    
    # Обработка команд для управления задачами
    if user_message.lower().startswith(('/задачи', '/tasks', 'задачи', 'tasks')):
        await show_tasks_menu(message, user_data)
        return
    elif user_message.lower().startswith(('/новая', '/new', 'новая задача', 'создать задачу')):
        await start_task_creation(message, user_data)
        return
    elif user_message.lower().startswith(('/меню', '/menu', 'меню')):
        await show_main_menu(message, user_data)
        return
    
    # Если пользователь в процессе создания задачи
    if user_data.current_view == "creating_task":
        await handle_task_creation_input(message, user_data)
        return
    
    # Если пользователь общался с AI-ментором, продолжаем общение
    if user_data.met_ai_mentor and user_message and not user_message.startswith('/'):
        ai_response = await chat_with_ai_mentor(user_data, user_message)
        await message.answer(f"🤖 **AI-ментор:**\n\n{ai_response}", parse_mode="Markdown")
        return
    
    # Показываем главное меню по умолчанию
    await show_main_menu(message, user_data)

# === UI функции для работы с задачами ===

async def show_main_menu(message: types.Message, user_data: TrackerUserData):
    """Показывает главное меню трекера"""
    user_data.current_view = "main"
    save_user_data(user_data)
    
    # Подсчет задач по статусам
    pending_count = len(get_tasks_by_status(user_data, TaskStatus.PENDING))
    in_progress_count = len(get_tasks_by_status(user_data, TaskStatus.IN_PROGRESS))
    completed_count = len(get_tasks_by_status(user_data, TaskStatus.COMPLETED))
    total_tasks = len(user_data.tasks)
    
    text = (
        f"🎯 **Главное меню трекера**\n\n"
        f"📊 **Статистика задач:**\n"
        f"• Всего задач: {total_tasks}\n"
        f"• ⏳ Ожидают: {pending_count}\n"
        f"• 🔄 В работе: {in_progress_count}\n"
        f"• ✅ Выполнены: {completed_count}\n\n"
        f"Выберите действие:"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📋 Мои задачи", callback_data="tracker_show_tasks")],
        [types.InlineKeyboardButton(text="➕ Новая задача", callback_data="tracker_new_task")],
        [types.InlineKeyboardButton(text="🤖 AI-ментор", callback_data="tracker_ai_mentor_chat")],
        [types.InlineKeyboardButton(text="⚙️ Настройки", callback_data="tracker_settings")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def show_tasks_menu(message: types.Message, user_data: TrackerUserData):
    """Показывает меню с задачами"""
    user_data.current_view = "tasks"
    save_user_data(user_data)
    
    if not user_data.tasks:
        text = (
            f"📋 **Мои задачи**\n\n"
            f"У вас пока нет задач. Создайте первую задачу!"
        )
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Создать задачу", callback_data="tracker_new_task")],
            [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="tracker_main_menu")]
        ])
    else:
        # Получаем задачи, отсортированные по приоритету и статусу
        sorted_tasks = get_tasks_sorted(user_data, "priority")
        
        text = f"📋 **Мои задачи** ({len(user_data.tasks)})\n\n"
        
        # Показываем первые 5 задач
        for i, task in enumerate(sorted_tasks[:5]):
            text += f"{i+1}. {format_task_text(task, user_data=user_data)}\n"
        
        if len(sorted_tasks) > 5:
            text += f"\n... и еще {len(sorted_tasks) - 5} задач"
        
        keyboard_rows = []
        
        # Кнопки для первых задач
        for i, task in enumerate(sorted_tasks[:3]):
            button_text = f"{i+1}. {task.title[:20]}{'...' if len(task.title) > 20 else ''}"
            keyboard_rows.append([types.InlineKeyboardButton(
                text=button_text, 
                callback_data=f"tracker_task_detail_{task.id}"
            )])
        
        # Дополнительные кнопки
        keyboard_rows.extend([
            [
                types.InlineKeyboardButton(text="📋 Все задачи", callback_data="tracker_all_tasks"),
                types.InlineKeyboardButton(text="➕ Новая", callback_data="tracker_new_task")
            ],
            [
                types.InlineKeyboardButton(text="🔄 В работе", callback_data="tracker_filter_in_progress"),
                types.InlineKeyboardButton(text="✅ Выполнены", callback_data="tracker_filter_completed")
            ],
            [types.InlineKeyboardButton(text="⬅️ Главное меню", callback_data="tracker_main_menu")]
        ])
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def start_task_creation(message: types.Message, user_data: TrackerUserData):
    """Начинает процесс создания новой задачи"""
    user_data.current_view = "creating_task"
    save_user_data(user_data)
    
    text = (
        f"➕ **Создание новой задачи**\n\n"
        f"Напишите название задачи:"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="tracker_cancel_creation")]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def handle_task_creation_input(message: types.Message, user_data: TrackerUserData):
    """Обрабатывает ввод при создании задачи"""
    task_title = message.text.strip()
    
    if not task_title or len(task_title) < 3:
        await message.answer(
            "❌ Название задачи должно содержать минимум 3 символа. Попробуйте еще раз:",
            parse_mode="Markdown"
        )
        return
    
    # Создаем задачу
    task = create_task(user_data, task_title)
    user_data.current_view = "main"
    save_user_data(user_data)
    
    text = (
        f"✅ **Задача создана!**\n\n"
        f"{format_task_text(task, show_details=True, user_data=user_data)}\n\n"
        f"Хотите настроить приоритет или описание?"
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🎯 Приоритет", callback_data=f"tracker_edit_priority_{task.id}"),
            types.InlineKeyboardButton(text="📝 Описание", callback_data=f"tracker_edit_description_{task.id}")
        ],
        [
            types.InlineKeyboardButton(text="▶️ Начать работу", callback_data=f"tracker_start_task_{task.id}"),
            types.InlineKeyboardButton(text="📋 К задачам", callback_data="tracker_show_tasks")
        ]
    ])
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def show_task_detail(message: types.Message, user_data: TrackerUserData, task_id: str):
    """Показывает детали задачи"""
    task = get_task_by_id(user_data, task_id)
    if not task:
        await message.answer("❌ Задача не найдена", parse_mode="Markdown")
        return
    
    text = (
        f"📋 **Детали задачи**\n\n"
        f"{format_task_text(task, show_details=True, user_data=user_data)}"
    )
    
    keyboard_rows = []
    
    # Кнопки управления статусом
    if task.status == TaskStatus.PENDING:
        keyboard_rows.append([
            types.InlineKeyboardButton(text="▶️ Начать", callback_data=f"tracker_start_task_{task.id}"),
            types.InlineKeyboardButton(text="✅ Завершить", callback_data=f"tracker_complete_task_{task.id}")
        ])
    elif task.status == TaskStatus.IN_PROGRESS:
        keyboard_rows.append([
            types.InlineKeyboardButton(text="⏸️ Приостановить", callback_data=f"tracker_pause_task_{task.id}"),
            types.InlineKeyboardButton(text="✅ Завершить", callback_data=f"tracker_complete_task_{task.id}")
        ])
    elif task.status == TaskStatus.COMPLETED:
        keyboard_rows.append([
            types.InlineKeyboardButton(text="🔄 Возобновить", callback_data=f"tracker_reopen_task_{task.id}")
        ])
    
    # Кнопки редактирования
    keyboard_rows.append([
        types.InlineKeyboardButton(text="🎯 Приоритет", callback_data=f"tracker_edit_priority_{task.id}"),
        types.InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"tracker_delete_task_{task.id}")
    ])
    
    # Навигация
    keyboard_rows.append([
        types.InlineKeyboardButton(text="⬅️ К задачам", callback_data="tracker_show_tasks")
    ])
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")

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